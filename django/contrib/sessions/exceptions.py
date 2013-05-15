from django.core.exceptions import SuspiciousOperation


class InvalidSessionKey(SuspiciousOperation):
    "Invalid characters in session key"
    pass
