from django.core.exceptions import ImproperlyConfigured


class InvalidEmailProvider(ImproperlyConfigured):
    """An email provider's OPTIONS are somehow not valid."""
