from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


class InvalidEmailProvider(ImproperlyConfigured):
    """An email provider's OPTIONS are somehow not valid."""


class EmailProviderDoesNotExist(InvalidEmailProvider, KeyError):
    """The requested alias is not defined in EMAIL_PROVIDERS."""

    def __init__(self, *, alias):
        # This is the only permitted use for this exception.
        super().__init__(f"The email provider '{alias}' is not configured.")


DEFAULT_EMAIL_PROVIDER_ALIAS = "default"

# Default value for an EMAIL_PROVIDERS "BACKEND".
# (Not related to the default email provider.)
DEFAULT_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class EmailProvidersHandler:
    def __getitem__(self, /, alias):
        return self.create_connection(
            alias if alias is not None else DEFAULT_EMAIL_PROVIDER_ALIAS
        )

    def __contains__(self, /, alias):
        return alias in self.settings

    def __iter__(self):
        return iter(self.settings)

    def get(self, alias=None, /, default=None):
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
            raise InvalidEmailProvider(
                f"EMAIL_PROVIDERS[{alias!r}]: 'alias' is not allowed in OPTIONS."
            )

        # RemovedInDjango70Warning.
        if _deprecated_kwargs:
            # get_connection() returning default provider with some overrides.
            # _ignore_unknown_kwargs tells BaseEmailBackend not to report these
            # keyword args as unknown OPTIONS.
            assert alias == DEFAULT_EMAIL_PROVIDER_ALIAS
            options = options | _deprecated_kwargs
            options |= {"_ignore_unknown_kwargs": _deprecated_kwargs.keys()}

        backend_path = config.get("BACKEND", DEFAULT_BACKEND)
        try:
            backend_class = import_string(backend_path)
        except ImportError as error:
            raise InvalidEmailProvider(
                f"EMAIL_PROVIDERS[{alias!r}]: Could not find BACKEND "
                f"'{backend_path}': {error}"
            ) from error
        return backend_class(alias=alias, **options)
