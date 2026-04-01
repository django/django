# RemovedInDjango70Warning: this entire file.
# Mailers-related deprecation warnings and helpers used in multiple places.
# (In a separate file to avoid circular import problems.)
import warnings

from django.conf import DEPRECATED_EMAIL_SETTINGS, settings
from django.utils.deprecation import (
    RemovedInDjango70Warning,
    django_file_prefixes,
)

FAIL_SILENTLY_ARG_WARNING = (
    "The 'fail_silently' argument is deprecated. See 'Migrating email to "
    "mailers' in Django's documentation for recommended replacements."
)
AUTH_ARGS_WARNING = (
    "The 'auth_user' and 'auth_password' arguments are deprecated. Set "
    "'username' and 'password' OPTIONS in MAILERS instead."
)
CONNECTION_ARG_WARNING = (
    "The 'connection' argument is deprecated. Switch to the 'using' argument "
    "with a MAILERS alias."
)
NO_DEFAULT_MAILER_WARNING = (
    "Django 7.0 will not have a default mailer. Configure "
    "settings.MAILERS to avoid errors when sending email."
)


def report_using_incompatibility(
    connection=None, fail_silently=False, auth_user=None, auth_password=None
):
    """Report arguments incompatible with 'using'."""
    if connection is not None:
        raise TypeError("'connection' is not compatible with 'using'.")
    if fail_silently:
        raise TypeError("'fail_silently' is not compatible with 'using'.")
    if auth_user is not None or auth_password is not None:
        raise TypeError(
            "'auth_user' and 'auth_password' are not compatible with 'using'. "
            "Set 'username' and 'password' OPTIONS in MAILERS instead."
        )


def warn_about_default_mailers_if_needed():
    if not hasattr(settings, "MAILERS"):
        # If a warning about migrating to MAILERS was not already
        # issued on startup (for a deprecated email setting), warn defining
        # MAILERS will be required for sending email in Django 7.0.
        if not any(
            hasattr(settings, name) and settings.is_overridden(name)
            for name in DEPRECATED_EMAIL_SETTINGS
        ):
            warnings.warn(
                NO_DEFAULT_MAILER_WARNING,
                RemovedInDjango70Warning,
                skip_file_prefixes=django_file_prefixes(),
            )
