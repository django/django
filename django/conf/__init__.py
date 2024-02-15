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
from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.functional import LazyObject, empty

ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"
DEFAULT_STORAGE_ALIAS = "default"
STATICFILES_STORAGE_ALIAS = "staticfiles"

# RemovedInDjango60Warning.
FORMS_URLFIELD_ASSUME_HTTPS_DEPRECATED_MSG = (
    "The FORMS_URLFIELD_ASSUME_HTTPS transitional setting is deprecated."
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
                % (desc, ENVIRONMENT_VARIABLE)
            )

        self._wrapped = Settings(settings_module)

    def __repr__(self):
        # Hardcode the class name as otherwise it yields 'Settings'.
        if self._wrapped is empty:
            return "<LazySettings [Unevaluated]>"
        return '<LazySettings "%(settings_module)s">' % {
            "settings_module": self._wrapped.SETTINGS_MODULE,
        }

    def __getattr__(self, name):
        """Return the value of a setting and cache it in self.__dict__."""
        if (_wrapped := self._wrapped) is empty:
            self._setup(name)
            _wrapped = self._wrapped
        val = getattr(_wrapped, name)

        # Special case some settings which require further modification.
        # This is done here for performance reasons so the modified value is cached.
        if name in {"MEDIA_URL", "STATIC_URL"} and val is not None:
            val = self._add_script_prefix(val)
        elif name == "SECRET_KEY" and not val:
            raise ImproperlyConfigured("The SECRET_KEY setting must not be empty.")

        self.__dict__[name] = val
        return val

    def __setattr__(self, name, value):
        """
        Set the value of setting. Clear all cached values if _wrapped changes
        (@override_settings does this) or clear single values when set.
        """
        if name == "_wrapped":
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
            raise RuntimeError("Settings already configured.")
        holder = UserSettingsHolder(default_settings)
        for name, value in options.items():
            if not name.isupper():
                raise TypeError("Setting %r must be uppercase." % name)
            setattr(holder, name, value)
        self._wrapped = holder

    @staticmethod
    def _add_script_prefix(value):
        """
        Add SCRIPT_NAME prefix to relative paths.

        Useful when the app is being served at a subpath and manually prefixing
        subpath to STATIC_URL and MEDIA_URL in settings is inconvenient.
        """
        # Don't apply prefix to absolute paths and URLs.
        if value.startswith(("http://", "https://", "/")):
            return value
        from django.urls import get_script_prefix

        return "%s%s" % (get_script_prefix(), value)

    @property
    def configured(self):
        """Return True if the settings have already been configured."""
        return self._wrapped is not empty

    def _show_deprecation_warning(self, message, category):
        stack = traceback.extract_stack()
        # Show a warning if the setting is used outside of Django.
        # Stack index: -1 this line, -2 the property, -3 the
        # LazyObject __getattribute__(), -4 the caller.
        filename, _, _, _ = stack[-4]
        if not filename.startswith(os.path.dirname(django.__file__)):
            warnings.warn(message, category, stacklevel=2)


class Settings:
    def __init__(self, settings_module):
        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting.isupper():
                setattr(self, setting, getattr(global_settings, setting))

        # store the settings module in case someone later cares
        self.SETTINGS_MODULE = settings_module

        mod = importlib.import_module(self.SETTINGS_MODULE)

        tuple_settings = (
            "ALLOWED_HOSTS",
            "INSTALLED_APPS",
            "TEMPLATE_DIRS",
            "LOCALE_PATHS",
            "SECRET_KEY_FALLBACKS",
        )
        self._explicit_settings = set()
        for setting in dir(mod):
            if setting.isupper():
                setting_value = getattr(mod, setting)

                if setting in tuple_settings and not isinstance(
                    setting_value, (list, tuple)
                ):
                    raise ImproperlyConfigured(
                        "The %s setting must be a list or a tuple." % setting
                    )
                setattr(self, setting, setting_value)
                self._explicit_settings.add(setting)

        if self.is_overridden("FORMS_URLFIELD_ASSUME_HTTPS"):
            warnings.warn(
                FORMS_URLFIELD_ASSUME_HTTPS_DEPRECATED_MSG,
                RemovedInDjango60Warning,
            )

        if hasattr(time, "tzset") and self.TIME_ZONE:
            # When we can, attempt to validate the timezone. If we can't find
            # this file, no check happens and it's harmless.
            zoneinfo_root = Path("/usr/share/zoneinfo")
            zone_info_file = zoneinfo_root.joinpath(*self.TIME_ZONE.split("/"))
            if zoneinfo_root.exists() and not zone_info_file.exists():
                raise ValueError("Incorrect timezone setting: %s" % self.TIME_ZONE)
            # Move the time zone info into os.environ. See ticket #2315 for why
            # we don't do this unconditionally (breaks Windows).
            os.environ["TZ"] = self.TIME_ZONE
            time.tzset()

    def is_overridden(self, setting):
        return setting in self._explicit_settings

    def __repr__(self):
        return '<%(cls)s "%(settings_module)s">' % {
            "cls": self.__class__.__name__,
            "settings_module": self.SETTINGS_MODULE,
        }


class UserSettingsHolder:
    """Holder for user configured settings."""

    # SETTINGS_MODULE doesn't make much sense in the manually configured
    # (standalone) case.
    SETTINGS_MODULE = None

    def __init__(self, default_settings):
        """
        Requests for configuration variables not in this class are satisfied
        from the module specified in default_settings (if possible).
        """
        self.__dict__["_deleted"] = set()
        self.default_settings = default_settings

    def __getattr__(self, name):
        if not name.isupper() or name in self._deleted:
            raise AttributeError
        return getattr(self.default_settings, name)

    def __setattr__(self, name, value):
        self._deleted.discard(name)
        if name == "FORMS_URLFIELD_ASSUME_HTTPS":
            warnings.warn(
                FORMS_URLFIELD_ASSUME_HTTPS_DEPRECATED_MSG,
                RemovedInDjango60Warning,
            )
        super().__setattr__(name, value)

    def __delattr__(self, name):
        self._deleted.add(name)
        if hasattr(self, name):
            super().__delattr__(name)

    def __dir__(self):
        return sorted(
            s
            for s in [*self.__dict__, *dir(self.default_settings)]
            if s not in self._deleted
        )

    def is_overridden(self, setting):
        deleted = setting in self._deleted
        set_locally = setting in self.__dict__
        set_on_default = getattr(
            self.default_settings, "is_overridden", lambda s: False
        )(setting)
        return deleted or set_locally or set_on_default

    def __repr__(self):
        return "<%(cls)s>" % {
            "cls": self.__class__.__name__,
        }


settings = LazySettings()
