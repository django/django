from django.core.exceptions import ImproperlyConfigured


class InvalidMailer(ImproperlyConfigured):
    """A settings.MAILERS entry has a configuration error."""

    def __init__(self, msg, *, alias=None):
        if alias is not None:
            msg = f"MAILERS[{alias!r}]: {msg}"
        super().__init__(msg)


class MailerDoesNotExist(InvalidMailer, KeyError):
    """The requested alias is not defined in settings.MAILERS."""

    def __init__(self, *, alias):
        # This is the only permitted use for this exception.
        super().__init__(f"The mailer '{alias}' is not configured.")
