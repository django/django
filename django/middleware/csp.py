import secrets
from http import HTTPStatus

from django.conf import settings
from django.middleware.constants import CSP
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject, empty


class LazyNonce(SimpleLazyObject):
    """
    Lazily generates a cryptographically secure nonce string, for use in CSP headers.

    The nonce is only generated when first accessed (e.g., via string
    interpolation or inside a template).

    The nonce will evaluate as `True` if it has been generated, and `False` if
    it has not. This is useful for third-party Django libraries that want to
    support CSP without requiring it.

    Example Django template usage:

        <script{% if request.csp_nonce %} nonce="{{ request.csp_nonce }}"...{% endif %}>

    The `{% if %}` block will only render if the nonce has been evaluated elsewhere.

    """

    def __init__(self):
        super().__init__(self._generate)

    def _generate(self):
        return secrets.token_urlsafe(16)

    def __bool__(self):
        return self._wrapped is not empty


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.csp_nonce = LazyNonce()

    def process_response(self, request, response):
        # In DEBUG mode, exclude CSP headers for specific status codes that
        # trigger the debug view.
        exempted_status_codes = {
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
        }
        if settings.DEBUG and response.status_code in exempted_status_codes:
            return response

        # If headers are already set on the response, don't overwrite them.
        # This allows for views to set their own CSP headers as needed.
        for header, disable_attr in (
            ("Content-Security-Policy", "_csp_disabled"),
            ("Content-Security-Policy-Report-Only", "_csp_disabled_ro"),
        ):
            if header not in response and not getattr(response, disable_attr, False):
                config, nonce = self.get_policy(
                    request,
                    response,
                    report_only=(header == "Content-Security-Policy-Report-Only"),
                )
                if config:
                    response.headers[header] = self.build_policy(config, nonce)

        return response

    @staticmethod
    def get_policy(request, response, report_only=False):
        # If set, use the config overrides on the response set via decorators.
        # Otherwise, default to the CSP config(s) defined in settings.
        if report_only:
            config = (
                getattr(response, "_csp_config_ro", None)
                or settings.SECURE_CSP_REPORT_ONLY
                or None
            )
        else:
            config = (
                getattr(response, "_csp_config", None) or settings.SECURE_CSP or None
            )
        # Only provide the nonce if it exists on the request and is not empty.
        nonce = getattr(request, "csp_nonce", None) or None
        return (config, nonce)

    @staticmethod
    def build_policy(config, nonce=None):
        policy = []
        directives = config.get("DIRECTIVES", {})

        for directive, value in directives.items():
            if value in (None, False):
                continue
            elif value is True:
                rendered_value = ""
            else:
                if isinstance(value, set):
                    # Sort set values for consistency, preventing cache invalidation
                    # between requests and ensuring reliable browser caching
                    value = sorted(value)
                elif not isinstance(value, list | tuple):
                    value = [value]

                # Replace the nonce sentinel with the actual nonce value, if the
                # sentinel is found and nonce is provided, otherwise remove it.
                has_sentinel = CSP.NONCE in value
                if has_sentinel and nonce:
                    value = [f"'nonce-{nonce}'" if v == CSP.NONCE else v for v in value]
                elif has_sentinel:
                    value = [v for v in value if v != CSP.NONCE]

                if not value:
                    continue

                rendered_value = " ".join(value)
            policy.append(f"{directive} {rendered_value}".rstrip())
        return "; ".join(policy)
