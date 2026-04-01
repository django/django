from django.core.exceptions import ImproperlyConfigured


class InvalidMailer(ImproperlyConfigured):
    """There is a problem with OPTIONS in a settings.MAILERS entry."""

    def __init__(self, msg, *, alias=None):
        if alias is not None:
            msg = f"MAILERS[{alias!r}]: {msg}"
        super().__init__(msg)
