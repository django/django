"""
Settings and configuration for Django.

Read values from the module specified by the DJANGO_SETTINGS_MODULE environment
variable, and then from django.conf.global_settings; see the global_settings.py
for a list of all possible variables.
"""

import importlib
import os
import time
import warnings
from pathlib import Path

from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import (
    RemovedInDjango70Warning,
    django_file_prefixes,
    warn_about_external_use,
)
from django.utils.functional import LazyObject, empty

ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"
DEFAULT_STORAGE_ALIAS = "default"
STATICFILES_STORAGE_ALIAS = "staticfiles"

USE_BLANK_CHOICE_DASH_DEPRECATED_MSG = (
    "The USE_BLANK_CHOICE_DASH setting is deprecated. If you wish to define "
    "your own default blank choice label, override "
    "django.db.models.fields.BLANK_CHOICE_LABEL in your app's ready() method."
)

# RemovedInDjango70Warning.
DEPRECATED_EMAIL_SETTINGS = {
    "EMAIL_BACKEND",
    "EMAIL_FILE_PATH",
    "EMAIL_HOST",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_HOST_USER",
    "EMAIL_PORT",
    "EMAIL_SSL_CERTFILE",
    "EMAIL_SSL_KEYFILE",
    "EMAIL_TIMEOUT",
    "EMAIL_USE_SSL",
    "EMAIL_USE_TLS",
}
EMAIL_SETTING_DEPRECATED_MSG = (
    "The {name} setting is deprecated. Migrate to MAILERS before Django 7.0."
)


# RemovedInDjango70Warning.
# Must be called with the complete set of user-defined setting names (but no
# default settings).
def _check_email_settings_conflicts(explicit_settings):
    deprecated = DEPRECATED_EMAIL_SETTINGS.intersection(explicit_settings)
    if deprecated and "MAILERS" in explicit_settings:
        deprecated_str = ", ".join(sorted(deprecated))
        raise ImproperlyConfigured(
            "Deprecated email settings are not allowed when MAILERS is "
            f"defined: {deprecated_str}."
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

        # RemovedInDjango70Warning.
        if name in DEPRECATED_EMAIL_SETTINGS:
            if hasattr(_wrapped, "MAILERS"):
                raise AttributeError(
                    f"The {name} setting is not available when MAILERS is defined."
                )
            _show_settings_deprecation_warning(
                EMAIL_SETTING_DEPRECATED_MSG.format(name=name), RemovedInDjango70Warning
            )

        # Special case some settings which require further modification.
        # This is done here for performance reasons so the modified value is
        # cached.
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

        # RemovedInDjango70Warning.
        if name == "MAILERS":
            # When MAILERS is set, clear any cached values of
            # deprecated settings so that __getattr__() runs again for them.
            for setting in DEPRECATED_EMAIL_SETTINGS:
                self.__dict__.pop(setting, None)
        if name in DEPRECATED_EMAIL_SETTINGS:
            _show_settings_deprecation_warning(
                EMAIL_SETTING_DEPRECATED_MSG.format(name=name), RemovedInDjango70Warning
            )

        super().__setattr__(name, value)

    def __delattr__(self, name):
        """Delete a setting and clear it from cache if needed."""
        super().__delattr__(name)
        self.__dict__.pop(name, None)

    # RemovedInDjango70Warning.
    def __dir__(self):
        attrs = super().__dir__()
        if hasattr(self._wrapped, "MAILERS"):
            # When MAILERS is defined, filter out deprecated email
            # settings that are from the global_settings defaults.
            attrs = [
                name
                for name in attrs
                if name not in DEPRECATED_EMAIL_SETTINGS
                or self._wrapped.is_overridden(name)
            ]
        return attrs

    def configure(self, default_settings=global_settings, **options):
        """
        Called to manually configure the settings. The 'default_settings'
        parameter sets where to retrieve any unspecified values from (its
        argument must support attribute access (__getattr__)).
        """
        if self._wrapped is not empty:
            raise RuntimeError("Settings already configured.")

        # RemovedInDjango70Warning.
        _check_email_settings_conflicts(options.keys())

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


class Settings:
    def __init__(self, settings_module):
        # update this dict from global settings (but only for ALL_CAPS
        # settings)
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

        # RemovedInDjango70Warning.
        _check_email_settings_conflicts(self._explicit_settings)
        for name in DEPRECATED_EMAIL_SETTINGS.intersection(self._explicit_settings):
            warnings.warn(
                EMAIL_SETTING_DEPRECATED_MSG.format(name=name),
                RemovedInDjango70Warning,
                skip_file_prefixes=django_file_prefixes(),
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
        if name == "USE_BLANK_CHOICE_DASH":
            warnings.warn(
                USE_BLANK_CHOICE_DASH_DEPRECATED_MSG,
                RemovedInDjango70Warning,
                skip_file_prefixes=django_file_prefixes(),
            )
        # RemovedInDjango70Warning.
        if name in DEPRECATED_EMAIL_SETTINGS:
            _show_settings_deprecation_warning(
                EMAIL_SETTING_DEPRECATED_MSG.format(name=name), RemovedInDjango70Warning
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


def _show_settings_deprecation_warning(message, category):
    """Issue a warning when external code uses a deprecated setting.

    Allow Django's own code to use the setting without emitting the warning.
    This function should only be called from within settings-related code.
    """
    warn_about_external_use(
        message,
        category,
        skip_name_prefixes=(
            # Include all settings-related code here. (Do not include all of
            # "django.conf", which would incorrectly identify any deprecated
            # settings usage inside django.conf.urls as external.)
            "django.conf.LazySettings",
            "django.conf.Settings",
            "django.conf.UserSettingsHolder",
            "django.utils.functional.LazyObject",  # LazySettings superclass.
            # override_settings() and similar test utils must be treated as
            # settings-related code, else deprecated settings usage in tests
            # would be incorrectly identified as internal.
            "django.test.utils.override_settings",
            "django.test.utils.modify_settings",
            "django.test.utils.TestContextDecorator",
            "django.test.testcases.SimpleTestCase.settings",
            "django.test.testcases.SimpleTestCase.modify_settings",
        ),
    )


settings = LazySettings()
