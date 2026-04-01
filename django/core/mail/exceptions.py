from django.core.exceptions import ImproperlyConfigured


class InvalidEmailProvider(ImproperlyConfigured):
    """There is a problem with OPTIONS in a settings.EMAIL_PROVIDERS entry."""

    def __init__(self, msg, *, alias=None):
        if alias is not None:
            msg = f"EMAIL_PROVIDERS[{alias!r}]: {msg}"
        super().__init__(msg)
