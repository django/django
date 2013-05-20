from django.core.exceptions import SuspiciousOperation


class DisallowedModeladminLookup(SuspiciousOperation):
    "Invalid filter was passed to admin view via URL querystring"
    pass
