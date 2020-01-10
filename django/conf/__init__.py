"""
Settings and configuration for Django.

Read values from the module specified by the DJANGO_SETTINGS_MODULE environment
variable, and then from django.conf.global_settings; see the global_settings.py
for a list of all possible variables.
"""

import importlib
import os
import time
import traceback
import warnings
from pathlib import Path

import django
from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import URLValidator
from django.utils.deprecation import RemovedInDjango40Warning
from django.utils.functional import LazyObject, empty

ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"

PASSWORD_RESET_TIMEOUT_DAYS_DEPRECATED_MSG = (
    'The PASSWORD_RESET_TIMEOUT_DAYS setting is deprecated. Use '
    'PASSWORD_RESET_TIMEOUT instead.'
)


class SettingsReference(str):
    """
    String subclass which references a current settings value. It's treated as
    the value in memory but serializes to a settings.NAME attribute reference.
    """
    def __new__(self, value, setting_name):
        return str.__new__(self, value)

    def __init__(self, value, setting_name):
        self.setting_name = setting_name


class LazySettings(LazyObject):
    """
    A lazy proxy for either global Django settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Django uses the settings module pointed to by DJANGO_SETTINGS_MODULE.
    """
    def _setup(self, name=None):
        """
        Load the settings module pointed to by the environment variable. This
        is used the first time settings are needed, if the user hasn't
        configured settings manually.
        """
        settings_module = os.environ.get(ENVIRONMENT_VARIABLE)
        if not settings_module:
            desc = ("setting %s" % name) if name else "settings"
            raise ImproperlyConfigured(
                "Requested %s, but settings are not configured. "
                "You must either define the environment variable %s "
                "or call settings.configure() before accessing settings."
                % (desc, ENVIRONMENT_VARIABLE))

        self._wrapped = Settings(settings_module)

    def __repr__(self):
        # Hardcode the class name as otherwise it yields 'Settings'.
        if self._wrapped is empty:
            return '<LazySettings [Unevaluated]>'
        return '<LazySettings "%(settings_module)s">' % {
            'settings_module': self._wrapped.SETTINGS_MODULE,
        }

    def __getattr__(self, name):
        """Return the value of a setting and cache it in self.__dict__."""
        if self._wrapped is empty:
            self._setup(name)
        val = getattr(self._wrapped, name)
        self.__dict__[name] = val
        return val

    def __setattr__(self, name, value):
        """
        Set the value of setting. Clear all cached values if _wrapped changes
        (@override_settings does this) or clear single values when set.
        """
        if name == '_wrapped':
            self.__dict__.clear()
        else:
            self.__dict__.pop(name, None)
        super().__setattr__(name, value)

    def __delattr__(self, name):
        """Delete a setting and clear it from cache if needed."""
        super().__delattr__(name)
        self.__dict__.pop(name, None)

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

    @staticmethod
    def _add_script_prefix(value):
        """
        Add SCRIPT_NAME prefix to relative paths.

        Useful when the app is being served at a subpath and manually prefixing
        subpath to STATIC_URL and MEDIA_URL in settings is inconvenient.
        """
        # Don't apply prefix to valid URLs.
        try:
            URLValidator()(value)
            return value
        except (ValidationError, AttributeError):
            pass
        # Don't apply prefix to absolute paths.
        if value.startswith('/'):
            return value
        from django.urls import get_script_prefix
        return '%s%s' % (get_script_prefix(), value)

    @property
    def configured(self):
        """Return True if the settings have already been configured."""
        return self._wrapped is not empty

    @property
    def PASSWORD_RESET_TIMEOUT_DAYS(self):
        stack = traceback.extract_stack()
        # Show a warning if the setting is used outside of Django.
        # Stack index: -1 this line, -2 the caller.
        filename, _, _, _ = stack[-2]
        if not filename.startswith(os.path.dirname(django.__file__)):
            warnings.warn(
                PASSWORD_RESET_TIMEOUT_DAYS_DEPRECATED_MSG,
                RemovedInDjango40Warning,
                stacklevel=2,
            )
        return self.__getattr__('PASSWORD_RESET_TIMEOUT_DAYS')

    @property
    def STATIC_URL(self):
        return self._add_script_prefix(self.__getattr__('STATIC_URL'))

    @property
    def MEDIA_URL(self):
        return self._add_script_prefix(self.__getattr__('MEDIA_URL'))


class BaseSettings:
    SETTINGS_MODULE = None

    def __init__(self, default_settings):
        self.__dict__['_explicit_settings'] = set()
        self.__dict__['default_settings'] = default_settings
        for setting in dir(default_settings):
            if setting.isupper():
                super().__setattr__(setting, getattr(default_settings, setting))

    def __setattr__(self, name, value):
        if not name.isupper():
            raise AttributeError("Can't set non-upper setting {}".format(name))
        if name == 'PASSWORD_RESET_TIMEOUT_DAYS':
            self.PASSWORD_RESET_TIMEOUT = value * 60 * 60 * 24
            warnings.warn(PASSWORD_RESET_TIMEOUT_DAYS_DEPRECATED_MSG, RemovedInDjango40Warning)
        super().__setattr__(name, value)
        self._explicit_settings.add(name)

    def __delattr__(self, name):
        if not name.isupper():
            raise AttributeError("Can't delete non-upper setting {}".format(name))
        super().__delattr__(name)
        self._explicit_settings.discard(name)

    def __repr__(self):
        class_name = self.__class__.__name__
        settings_module = self.SETTINGS_MODULE
        if settings_module:
            return '<{} "{}">'.format(class_name, settings_module)
        else:
            return '<{}>'.format(class_name)

    def is_overridden(self, setting):
        set_explicitly = setting in self._explicit_settings
        set_on_default = getattr(self.default_settings, 'is_overridden', lambda s: False)(setting)
        return set_explicitly or set_on_default


class Settings(BaseSettings):
    def __init__(self, settings_module):
        super().__init__(global_settings)
        self.SETTINGS_MODULE = settings_module

        mod = importlib.import_module(self.SETTINGS_MODULE)

        tuple_settings = (
            "INSTALLED_APPS",
            "TEMPLATE_DIRS",
            "LOCALE_PATHS",
        )
        for setting in dir(mod):
            if setting.isupper():
                setting_value = getattr(mod, setting)

                if (setting in tuple_settings and
                        not isinstance(setting_value, (list, tuple))):
                    raise ImproperlyConfigured("The %s setting must be a list or a tuple. " % setting)
                setattr(self, setting, setting_value)

        if not self.SECRET_KEY:
            raise ImproperlyConfigured("The SECRET_KEY setting must not be empty.")

        if self.is_overridden('PASSWORD_RESET_TIMEOUT_DAYS') and self.is_overridden('PASSWORD_RESET_TIMEOUT'):
            raise ImproperlyConfigured(
                'PASSWORD_RESET_TIMEOUT_DAYS/PASSWORD_RESET_TIMEOUT are '
                'mutually exclusive.'
            )

        if hasattr(time, 'tzset') and self.TIME_ZONE:
            # When we can, attempt to validate the timezone. If we can't find
            # this file, no check happens and it's harmless.
            zoneinfo_root = Path('/usr/share/zoneinfo')
            zone_info_file = zoneinfo_root.joinpath(*self.TIME_ZONE.split('/'))
            if zoneinfo_root.exists() and not zone_info_file.exists():
                raise ValueError("Incorrect timezone setting: %s" % self.TIME_ZONE)
            # Move the time zone info into os.environ. See ticket #2315 for why
            # we don't do this unconditionally (breaks Windows).
            os.environ['TZ'] = self.TIME_ZONE
            time.tzset()


class UserSettingsHolder(BaseSettings):
    """Holder for user configured settings."""


settings = LazySettings()
