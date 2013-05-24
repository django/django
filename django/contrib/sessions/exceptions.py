from django.core.exceptions import SuspiciousOperation


class InvalidSessionKey(SuspiciousOperation):
    """Invalid characters in session key"""
    pass


class SuspiciousSession(SuspiciousOperation):
    """The session may be tampered with"""
    pass
