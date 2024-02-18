"""Module contains checks related to Django settings."""

from django.conf import global_settings, settings
from django.utils.functional import Promise
from django.utils.text import Truncator
from django.utils.version import get_docs_version

from . import Tags, Warning, register


def module_to_dict(module, omittable=lambda k: k.startswith("_") or not k.isupper()):
    """Convert a module namespace to a Python dictionary.

    This is a copy of
    :py:meth:`django.core.management.commands.diffsettings.module_to_dict`
    to avoid circular imports.
    """
    return {k: getattr(module, k) for k in dir(module) if not omittable(k)}


# The types for settings that have None as a default value or can have more than one
# disjunctive type
default_settings_types = {
    "CSRF_COOKIE_DOMAIN": (str,),
    "EMAIL_SSL_CERTFILE": (str,),
    "EMAIL_SSL_KEYFILE": (str,),
    "EMAIL_TIMEOUT": (int,),
    "FILE_UPLOAD_DIRECTORY_PERMISSIONS": (int,),
    "FILE_UPLOAD_TEMP_DIR": (str,),
    "FORCE_SCRIPT_NAME": (str,),
    "FORMAT_MODULE_PATH": (str,),
    "LANGUAGE_COOKIE_AGE": (int,),
    "LANGUAGE_COOKIE_DOMAIN": (str,),
    "LANGUAGE_COOKIE_SAMESITE": (str,),
    "LOGGING": (str, dict),
    "LOGOUT_REDIRECT_URL": (str,),
    "SECURE_PROXY_SSL_HEADER": (tuple,),
    "SECURE_SSL_HOST": (str,),
    "SESSION_COOKIE_DOMAIN": (str,),
    "SESSION_COOKIE_SAMESITE": (str, bool),
    "SESSION_FILE_PATH": (str,),
    "STATIC_ROOT": (str,),
    "STATIC_URL": (str,),
    "WSGI_APPLICATION": (str,),
}


@register(Tags.settings)
def check_settings_types(app_configs, **kwargs):
    """Check types of global user settings.

    The type of a user setting is checked to be of the same type as or subtype of the
    default value for that setting.

    If the default value for a setting is None or there are more than one disjunctive
    types possible, the types are determined from :py:data:`default_settings_types`.

    """
    user_settings = module_to_dict(settings._wrapped)
    default_settings = module_to_dict(global_settings)

    warnings = []
    for setting in user_settings:
        # Only check Django settings
        if setting not in default_settings:
            continue
        default_value = default_settings[setting]
        user_value = user_settings[setting]
        if isinstance(user_value, Promise) or user_value is default_value:
            continue
        # default_types for setting is a tuple of types either taken
        # from :py:data:`default_settings_types` or
        # is a tuple with the single type for the default_value or
        # None if the default_value is None
        default_types = default_settings_types.get(
            setting, (type(default_value),) if default_value is not None else None
        )
        if default_types is not None and not any(
            isinstance(user_value, default_type) for default_type in default_types
        ):
            default_sample = Truncator(repr(default_value)).words(5)
            warnings.append(
                Warning(
                    f"The type of the {setting} setting should be "
                    f"{' or '.join(type.__name__ for type in default_types)}"
                    f"{' or None' if default_value is None else ''}"
                    ".",
                    hint=f"default is {default_sample}"
                    f" (see https://docs.djangoproject.com/en/{get_docs_version()}"
                    f"/ref/settings/#std-setting-{setting}).",
                    id="settings.W001",
                )
            )
            # warnings.append(Warning(f"{type(user_value)} {user_value}"))
    return warnings
