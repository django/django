"""
Settings and configuration for Django.

Values will be read from the module specified by the DJANGO_SETTINGS_MODULE environment
variable, and then from django.conf.global_settings; see the global settings file for
a list of all possible variables.
"""

import importlib
import logging
import os
import sys
import time     # Needed for Windows
import warnings

from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import LazyObject, empty
from django.utils.module_loading import import_by_path
from django.utils import six

ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"


class LazySettings(LazyObject):
    """
    A lazy proxy for either global Django settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Django uses the settings module pointed to by DJANGO_SETTINGS_MODULE.
    """
    def _setup(self, name=None):
        """
        Load the settings module pointed to by the environment variable. This
        is used the first time we need any settings at all, if the user has not
        previously configured the settings manually.
        """
        try:
            settings_module = os.environ[ENVIRONMENT_VARIABLE]
            if not settings_module: # If it's set but is an empty string.
                raise KeyError
        except KeyError:
            desc = ("setting %s" % name) if name else "settings"
            raise ImproperlyConfigured(
                "Requested %s, but settings are not configured. "
                "You must either define the environment variable %s "
                "or call settings.configure() before accessing settings."
                % (desc, ENVIRONMENT_VARIABLE))

        self._wrapped = Settings(settings_module)
        self._configure_logging()

    def __getattr__(self, name):
        if self._wrapped is empty:
            self._setup(name)
        return getattr(self._wrapped, name)

    def _configure_logging(self):
        """
        Setup logging from LOGGING_CONFIG and LOGGING settings.
        """
        if not sys.warnoptions:
            # Route warnings through python logging
            logging.captureWarnings(True)
            # Allow DeprecationWarnings through the warnings filters
            warnings.simplefilter("default", DeprecationWarning)

        if self.LOGGING_CONFIG:
            from django.utils.log import DEFAULT_LOGGING
            # First find the logging configuration function ...
            logging_config_func = import_by_path(self.LOGGING_CONFIG)

            logging_config_func(DEFAULT_LOGGING)

            # ... then invoke it with the logging settings
            if self.LOGGING:
                logging_config_func(self.LOGGING)

    def configure(self, default_settings=global_settings, **options):
        """
        Called to manually configure the settings. The 'default_settings'
        parameter sets where to retrieve any unspecified values from (its
        argument must support attribute access (__getattr__)).
        """
        if self._wrapped is not empty:
            raise RuntimeError('Settings already configured.')
        holder = UserSettingsHolder(default_settings)
        for name, value in options.items():
            setattr(holder, name, value)
        self._wrapped = holder
        self._configure_logging()

    @property
    def configured(self):
        """
        Returns True if the settings have already been configured.
        """
        return self._wrapped is not empty


# Deprecation of *_COOKIE_* settings in Django 1.7. Remove in 1.9.
_DEPRECATED_COOKIE_SETTINGS = ('LANGUAGE_COOKIE_NAME',

    'SESSION_COOKIE_NAME', 'SESSION_COOKIE_AGE',
    'SESSION_COOKIE_DOMAIN', 'SESSION_COOKIE_SECURE', 'SESSION_COOKIE_PATH',
    'SESSION_COOKIE_HTTPONLY',

    'CSRF_COOKIE_NAME', 'CSRF_COOKIE_DOMAIN', 'CSRF_COOKIE_SECURE',
    'CSRF_COOKIE_PATH', 'CSRF_COOKIE_HTTPONLY')

# Deprecation of *_COOKIE_* settings in Django 1.7. Remove in 1.9.
def cookie_settings_deprecation_check(setting):
    if setting in _DEPRECATED_COOKIE_SETTINGS:
        prefix, _, attrib = setting.split('_', 2)
        new = '%s_COOKIE' % prefix
        warnings.warn("The %(old)s setting is deprecated. Use the new %(new)s dict setting instead."
                      % {'old': setting, 'new': new},
            PendingDeprecationWarning, stacklevel=3)
        return (new, attrib)
    return False

# Deprecation of *_COOKIE_* settings in Django 1.7. Remove in 1.9
def port_cookie_setting(obj, old_setting, setting_value):
    vals = cookie_settings_deprecation_check(old_setting)
    if vals:
        new_setting, cookie_attrib = vals
        temp = getattr(obj, new_setting)
        temp[cookie_attrib] = setting_value
        setattr(obj, new_setting, temp)
    return vals


class BaseSettings(object):
    """
    Common logic for settings whether set by a module or by the user.
    """
    def __setattr__(self, name, value):
        if name in ("MEDIA_URL", "STATIC_URL") and value and not value.endswith('/'):
            raise ImproperlyConfigured("If set, %s must end with a slash" % name)
        elif name == "ALLOWED_INCLUDE_ROOTS" and isinstance(value, six.string_types):
            raise ValueError("The ALLOWED_INCLUDE_ROOTS setting must be set "
                "to a tuple, not a string.")
        elif name == "INSTALLED_APPS":
            value = list(value)  # force evaluation of generators on Python 3
            if len(value) != len(set(value)):
                raise ImproperlyConfigured("The INSTALLED_APPS setting must contain unique values.")

        object.__setattr__(self, name, value)


class Settings(BaseSettings):
    def __init__(self, settings_module):
        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting == setting.upper():
                setattr(self, setting, getattr(global_settings, setting))

        # store the settings module in case someone later cares
        self.SETTINGS_MODULE = settings_module

        try:
            mod = importlib.import_module(self.SETTINGS_MODULE)
        except ImportError as e:
            raise ImportError(
                "Could not import settings '%s' (Is it on sys.path? Is there an import error in the settings file?): %s"
                % (self.SETTINGS_MODULE, e)
            )

        tuple_settings = ("INSTALLED_APPS", "TEMPLATE_DIRS")

        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)

                if setting in tuple_settings and \
                        isinstance(setting_value, six.string_types):
                    raise ImproperlyConfigured("The %s setting must be a tuple. "
                            "Please fix your settings." % setting)

                # Deprecation of *_COOKIE_* settings in Django 1.7. Remove in 1.9
                if port_cookie_setting(self, setting, setting_value):
                    continue

                setattr(self, setting, setting_value)

        if not self.SECRET_KEY:
            raise ImproperlyConfigured("The SECRET_KEY setting must not be empty.")

        if hasattr(time, 'tzset') and self.TIME_ZONE:
            # When we can, attempt to validate the timezone. If we can't find
            # this file, no check happens and it's harmless.
            zoneinfo_root = '/usr/share/zoneinfo'
            if (os.path.exists(zoneinfo_root) and not
                    os.path.exists(os.path.join(zoneinfo_root, *(self.TIME_ZONE.split('/'))))):
                raise ValueError("Incorrect timezone setting: %s" % self.TIME_ZONE)
            # Move the time zone info into os.environ. See ticket #2315 for why
            # we don't do this unconditionally (breaks Windows).
            os.environ['TZ'] = self.TIME_ZONE
            time.tzset()


class UserSettingsHolder(BaseSettings):
    """
    Holder for user configured settings.
    """
    # SETTINGS_MODULE doesn't make much sense in the manually configured
    # (standalone) case.
    SETTINGS_MODULE = None

    def __init__(self, default_settings):
        """
        Requests for configuration variables not in this class are satisfied
        from the module specified in default_settings (if possible).
        """
        self.__dict__['_deleted'] = set()
        self.default_settings = default_settings

    def __getattr__(self, name):
        if name in self._deleted:
            raise AttributeError
        return getattr(self.default_settings, name)

    def __setattr__(self, name, value):
        self._deleted.discard(name)
        # Deprecation of *_COOKIE_* settings in Django 1.7. Remove in 1.9
        port_cookie_setting(self, name, value)
        return super(UserSettingsHolder, self).__setattr__(name, value)

    def __delattr__(self, name):
        self._deleted.add(name)
        return super(UserSettingsHolder, self).__delattr__(name)

    def __dir__(self):
        return list(self.__dict__) + dir(self.default_settings)

settings = LazySettings()
