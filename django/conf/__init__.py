"""
Settings and configuration for Django.

Values will be read from the module specified by the DJANGO_SETTINGS_MODULE environment
variable, and then from django.conf.global_settings; see the global settings file for
a list of all possible variables.
"""

import os
import re
import time     # Needed for Windows
import warnings

from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import LazyObject, empty
from django.utils import importlib

ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"


class LazySettings(LazyObject):
    """
    A lazy proxy for either global Django settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Django uses the settings module pointed to by DJANGO_SETTINGS_MODULE.
    """
    def _setup(self):
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
            # NOTE: This is arguably an EnvironmentError, but that causes
            # problems with Python's interactive help.
            raise ImportError("Settings cannot be imported, because environment variable %s is undefined." % ENVIRONMENT_VARIABLE)

        self._wrapped = Settings(settings_module)

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

    @property
    def configured(self):
        """
        Returns True if the settings have already been configured.
        """
        return self._wrapped is not empty


class BaseSettings(object):
    """
    Common logic for settings whether set by a module or by the user.
    """
    def __setattr__(self, name, value):
        if name in ("MEDIA_URL", "STATIC_URL") and value and not value.endswith('/'):
            raise ImproperlyConfigured("If set, %s must end with a slash" % name)
        elif name == "ADMIN_MEDIA_PREFIX":
            warnings.warn("The ADMIN_MEDIA_PREFIX setting has been removed; "
                          "use STATIC_URL instead.", DeprecationWarning)
        elif name == "ALLOWED_INCLUDE_ROOTS" and isinstance(value, basestring):
            raise ValueError("The ALLOWED_INCLUDE_ROOTS setting must be set "
                "to a tuple, not a string.")
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
        except ImportError, e:
            raise ImportError("Could not import settings '%s' (Is it on sys.path?): %s" % (self.SETTINGS_MODULE, e))

        # Settings that should be converted into tuples if they're mistakenly entered
        # as strings.
        tuple_settings = ("INSTALLED_APPS", "TEMPLATE_DIRS")

        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)
                if setting in tuple_settings and \
                        isinstance(setting_value, basestring):
                    setting_value = (setting_value,) # In case the user forgot the comma.
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

        # Settings are configured, so we can set up the logger if required
        if self.LOGGING_CONFIG:
            # First find the logging configuration function ...
            logging_config_path, logging_config_func_name = self.LOGGING_CONFIG.rsplit('.', 1)
            logging_config_module = importlib.import_module(logging_config_path)
            logging_config_func = getattr(logging_config_module, logging_config_func_name)

            # Backwards-compatibility shim for #16288 fix
            compat_patch_logging_config(self.LOGGING)

            # ... then invoke it with the logging settings
            logging_config_func(self.LOGGING)


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
        self.default_settings = default_settings

    def __getattr__(self, name):
        return getattr(self.default_settings, name)

    def __dir__(self):
        return self.__dict__.keys() + dir(self.default_settings)

    # For Python < 2.6:
    __members__ = property(lambda self: self.__dir__())

settings = LazySettings()



def compat_patch_logging_config(logging_config):
    """
    Backwards-compatibility shim for #16288 fix. Takes initial value of
    ``LOGGING`` setting and patches it in-place (issuing deprecation warning)
    if "mail_admins" logging handler is configured but has no filters.

    """
    #  Shim only if LOGGING["handlers"]["mail_admins"] exists,
    #  but has no "filters" key
    if "filters" not in logging_config.get(
        "handlers", {}).get(
        "mail_admins", {"filters": []}):

        warnings.warn(
            "You have no filters defined on the 'mail_admins' logging "
            "handler: adding implicit debug-false-only filter. "
            "See http://docs.djangoproject.com/en/dev/releases/1.4/"
            "#request-exceptions-are-now-always-logged",
            PendingDeprecationWarning)

        filter_name = "require_debug_false"

        filters = logging_config.setdefault("filters", {})
        while filter_name in filters:
            filter_name = filter_name + "_"

        filters[filter_name] = {
            "()": "django.utils.log.RequireDebugFalse",
        }

        logging_config["handlers"]["mail_admins"]["filters"] = [filter_name]
