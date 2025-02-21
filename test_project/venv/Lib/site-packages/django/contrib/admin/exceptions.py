from django.core.exceptions import SuspiciousOperation


class DisallowedModelAdminLookup(SuspiciousOperation):
    """Invalid filter was passed to admin view via URL querystring"""

    pass


class DisallowedModelAdminToField(SuspiciousOperation):
    """Invalid to_field was passed to admin view via URL query string"""

    pass


class AlreadyRegistered(Exception):
    """The model is already registered."""

    pass


class NotRegistered(Exception):
    """The model is not registered."""

    pass
