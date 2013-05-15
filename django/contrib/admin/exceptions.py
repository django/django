from django.core.exceptions import SuspiciousOperation


class DissallowedModeladminLookup(SuspiciousOperation):
    "Invalid filter was passed to admin view via URL querystring"
    pass
