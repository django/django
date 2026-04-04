# RemovedInDjango70Warning: this entire file.
# mail.providers-related deprecation warnings and helpers used in multiple
# places. (In a separate file to avoid circular import problems.)


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
