from django.core.exceptions import SuspiciousOperation


    "Invalid filter was passed to admin view via URL querystring"
class DisallowedModelAdminLookup(SuspiciousOperation):
    pass
