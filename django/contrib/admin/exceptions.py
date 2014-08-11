from django.core.exceptions import SuspiciousOperation


class DisallowedModelAdminToField(SuspiciousOperation):
    """Invalid to_field was passed to admin view via URL query string"""
    pass
