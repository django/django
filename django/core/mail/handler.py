from django.conf import settings
from django.core.mail import InvalidMailer, MailerDoesNotExist
from django.utils.module_loading import import_string

DEFAULT_MAILER_ALIAS = "default"

# Default value for a MAILERS "BACKEND". (Not related to the default mailer.)
DEFAULT_MAILER_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class MailersHandler:
    def __getitem__(self, /, alias):
        return self.create_connection(alias)

    def __contains__(self, /, alias):
        return alias in self.settings

    def __iter__(self):
        return iter(self.settings)

    def get(self, alias, /, default=None):
        try:
            return self[alias]
        except MailerDoesNotExist:
            return default

    @property
    def default(self):
        return self[DEFAULT_MAILER_ALIAS]

    @property
    def settings(self):
        return settings.MAILERS

    def create_connection(self, alias, /):
        try:
            config = self.settings[alias]
        except KeyError:
            raise MailerDoesNotExist(alias=alias) from None

        options = config.get("OPTIONS", {})
        if "alias" in options:
            raise InvalidMailer("OPTIONS must not define 'alias'.", alias=alias)

        backend_path = config.get("BACKEND", DEFAULT_MAILER_BACKEND)
        try:
            backend_class = import_string(backend_path)
        except ImportError as error:
            raise InvalidMailer(
                f"Could not find BACKEND {backend_path!r}: {error}", alias=alias
            ) from error
        return backend_class(alias=alias, **options)
