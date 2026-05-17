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
        # RemovedInDjango70Warning: change to:
        #   return settings.MAILERS
        return getattr(settings, "MAILERS", {})

    # RemovedInDjango70Warning.
    @property
    def _is_configured(self):
        """True if settings.py has opted into MAILERS support."""
        return hasattr(settings, "MAILERS")

    # RemovedInDjango70Warning: _deprecated_kwargs.
    def create_connection(self, alias, /, *, _deprecated_kwargs=None):
        # RemovedInDjango70Warning.
        if not self._is_configured and alias == DEFAULT_MAILER_ALIAS:
            # Create mailers.default from deprecated settings.
            from django.core.mail import get_connection

            assert _deprecated_kwargs is None
            return get_connection()

        try:
            config = self.settings[alias]
        except KeyError:
            raise MailerDoesNotExist(alias=alias) from None

        options = config.get("OPTIONS", {})
        if "alias" in options:
            raise InvalidMailer("OPTIONS must not define 'alias'.", alias=alias)

        # RemovedInDjango70Warning.
        if _deprecated_kwargs:
            # Being called from get_connection() to create default mailer
            # instance with some overrides. _ignore_unknown_kwargs prevents
            # BaseEmailBackend from reporting these as unknown OPTIONS.
            assert alias == DEFAULT_MAILER_ALIAS
            options = options | _deprecated_kwargs
            options |= {"_ignore_unknown_kwargs": set(_deprecated_kwargs)}

        backend_path = config.get("BACKEND", DEFAULT_MAILER_BACKEND)
        try:
            backend_class = import_string(backend_path)
        except ImportError as error:
            raise InvalidMailer(
                f"Could not find BACKEND {backend_path!r}: {error}", alias=alias
            ) from error
        return backend_class(alias=alias, **options)
