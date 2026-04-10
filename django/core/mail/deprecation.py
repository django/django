# RemovedInDjango70Warning: this entire file.
# mail.mailers-related deprecation warnings and helpers used in multiple
# places. (In a separate file to avoid circular import problems.)
import warnings

from django.conf import DEPRECATED_EMAIL_SETTINGS, settings
from django.utils.deprecation import (
    RemovedInDjango70Warning,
    django_file_prefixes,
)

NO_DEFAULT_MAILER_WARNING = (
    "Django 7.0 will not have a default mailer. Configure "
    "settings.MAILERS to avoid errors sending email."
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
    needs_warning = not (
        hasattr(settings, "MAILERS")
        or any(
            hasattr(settings, name) and settings.is_overridden(name)
            for name in DEPRECATED_EMAIL_SETTINGS
        )
    )
    if needs_warning:
        warnings.warn(
            NO_DEFAULT_MAILER_WARNING,
            RemovedInDjango70Warning,
            skip_file_prefixes=django_file_prefixes(),
        )
