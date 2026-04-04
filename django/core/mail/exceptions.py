from django.core.exceptions import ImproperlyConfigured


class InvalidEmailProvider(ImproperlyConfigured):
    """There is a problem with OPTIONS in a settings.EMAIL_PROVIDERS entry."""

    def __init__(self, msg, *, alias=None):
        if alias is not None:
            msg = f"EMAIL_PROVIDERS[{alias!r}]: {msg}"
        super().__init__(msg)


class EmailProviderDoesNotExist(InvalidEmailProvider, KeyError):
    """The requested alias is not defined in settings.EMAIL_PROVIDERS."""

    def __init__(self, *, alias):
        # This is the only permitted use for this exception.
        super().__init__(f"The email provider '{alias}' is not configured.")
