# RemovedInDjango70Warning: this entire file.
# mail.providers-related deprecation warnings and helpers used in multiple
# places. (In a separate file to avoid circular import problems.)

FAIL_SILENTLY_ARG_WARNING = (
    "The 'fail_silently' argument is deprecated. See 'Migrating to "
    "EMAIL_PROVIDERS' in Django's documentation for recommended replacements."
)
AUTH_ARGS_WARNING = (
    "The 'auth_user' and 'auth_password' arguments are deprecated. Set "
    "'username' and 'password' OPTIONS in EMAIL_PROVIDERS instead."
)
CONNECTION_ARG_WARNING = (
    "The 'connection' argument is deprecated. Switch to the 'using' argument "
    "with an EMAIL_PROVIDERS alias."
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
            "Set 'username' and 'password' OPTIONS in EMAIL_PROVIDERS instead."
        )
