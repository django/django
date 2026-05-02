from django.conf import settings
from django.core.mail import EmailProviderDoesNotExist, InvalidEmailProvider
from django.utils.module_loading import import_string

DEFAULT_EMAIL_PROVIDER_ALIAS = "default"

# Default value for an EMAIL_PROVIDERS "BACKEND".
# (Not related to the default email provider.)
DEFAULT_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class EmailProvidersHandler:
    def __getitem__(self, /, alias):
        return self.create_connection(alias)

    def __contains__(self, /, alias):
        return alias in self.settings

    def __iter__(self):
        return iter(self.settings)

    def get(self, alias, /, default=None):
        try:
            return self[alias]
        except EmailProviderDoesNotExist:
            return default

    @property
    def default(self):
        return self[DEFAULT_EMAIL_PROVIDER_ALIAS]

    @property
    def settings(self):
        # RemovedInDjango70Warning: change to:
        #   return settings.EMAIL_PROVIDERS
        return getattr(settings, "EMAIL_PROVIDERS", {})

    # RemovedInDjango70Warning.
    @property
    def _is_configured(self):
        """True if settings.py has opted into EMAIL_PROVIDERS support."""
        return hasattr(settings, "EMAIL_PROVIDERS")

    # RemovedInDjango70Warning: _deprecated_kwargs.
    def create_connection(self, alias, /, *, _deprecated_kwargs=None):
        # RemovedInDjango70Warning.
        if not self._is_configured and alias == DEFAULT_EMAIL_PROVIDER_ALIAS:
            # Create providers.default from deprecated settings.
            from django.core.mail import get_connection

            assert _deprecated_kwargs is None
            return get_connection()

        try:
            config = self.settings[alias]
        except KeyError:
            raise EmailProviderDoesNotExist(alias=alias) from None

        options = config.get("OPTIONS", {})
        if "alias" in options:
            raise InvalidEmailProvider("OPTIONS must not define 'alias'.", alias=alias)

        # RemovedInDjango70Warning.
        if _deprecated_kwargs:
            # get_connection() returning default provider with some overrides.
            # _ignore_unknown_kwargs tells BaseEmailBackend not to report these
            # keyword args as unknown OPTIONS.
            assert alias == DEFAULT_EMAIL_PROVIDER_ALIAS
            options = options | _deprecated_kwargs
            options |= {"_ignore_unknown_kwargs": set(_deprecated_kwargs.keys())}

        backend_path = config.get("BACKEND", DEFAULT_BACKEND)
        try:
            backend_class = import_string(backend_path)
        except ImportError as error:
            raise InvalidEmailProvider(
                f"Could not find BACKEND {backend_path!r}: {error}", alias=alias
            ) from error
        return backend_class(alias=alias, **options)
