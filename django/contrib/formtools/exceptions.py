from django.core.exceptions import SuspiciousOperation


class WizardViewCookieModified(SuspiciousOperation):
    """Signature of cookie modified"""
    pass
