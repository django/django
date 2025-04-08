import base64
import os
from functools import partial

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

# TODO: Do we want to exclude CSP from a default set of views in DEBUG mode?

# TODO: Should we add a security check to warn if the CSP settings are empty
# that no CSP headers will be sent. (docs/refs/checks.txt)

HEADER = "Content-Security-Policy"
HEADER_REPORT_ONLY = "Content-Security-Policy-Report-Only"

NONE = "'none'"
REPORT_SAMPLE = "'report-sample'"
SELF = "'self'"
STRICT_DYNAMIC = "'strict-dynamic'"
UNSAFE_ALLOW_REDIRECTS = "'unsafe-allow-redirects'"
UNSAFE_EVAL = "'unsafe-eval'"
UNSAFE_HASHES = "'unsafe-hashes'"
UNSAFE_INLINE = "'unsafe-inline'"
WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"


class Nonce:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "django.middleware.csp.NONCE"


NONCE = Nonce()


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    def _make_nonce(self, request):
        # Ensure that any subsequent calls to request.csp_nonce return the same value
        if not getattr(request, "_csp_nonce", None):
            request._csp_nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        return request._csp_nonce

    def process_request(self, request):
        nonce = partial(self._make_nonce, request)
        request.csp_nonce = SimpleLazyObject(nonce)

    def process_response(self, request, response):
        # If headers are already set on the response, don't overwrite them.
        # This allows for views to set their own CSP headers as needed.
        no_csp_header = HEADER not in response
        is_not_exempt = getattr(response, "_csp_exempt", False) is False
        if no_csp_header and is_not_exempt:
            config, nonce = self.get_policy(request, response)
            if config:
                response.headers[HEADER] = self.build_policy(config, nonce)

        no_csp_header = HEADER_REPORT_ONLY not in response
        is_not_exempt = getattr(response, "_csp_exempt_ro", False) is False
        if no_csp_header and is_not_exempt:
            config, nonce = self.get_policy(request, response, report_only=True)
            if config:
                response.headers[HEADER_REPORT_ONLY] = self.build_policy(config, nonce)

        return response

    def get_policy(self, request, response, report_only=False):
        # If set, use the config overrides on the response set via decorators.
        # Otherwise, default to the CSP config(s) defined in settings.
        if report_only:
            config = getattr(response, "_csp_config_ro", None)
            if config is None:
                config = settings.SECURE_CSP_REPORT_ONLY or None
        else:
            config = getattr(response, "_csp_config", None)
            if config is None:
                config = settings.SECURE_CSP or None

        nonce = getattr(request, "_csp_nonce", None)

        return (config, nonce)

    # TODO: Make this cache-able?
    # This is challenging due to:
    # - Having the nonce, which is unique per request
    # - The decorators pass in their own configs
    def build_policy(self, config, nonce=None):
        policy = []
        directives = config.get("DIRECTIVES", {})

        for directive, value in directives.items():
            if value is None:
                continue
            if not isinstance(value, (list, tuple)):
                value = [value]
            if NONCE in value:
                if nonce:
                    value = [f"'nonce-{nonce}'" if v == NONCE else v for v in value]
                else:
                    # Remove the `NONCE` sentinel value if no nonce is provided.
                    value = [v for v in value if v != NONCE]
            if len(value):
                # Support boolean directives, like `upgrade-insecure-requests`.
                if value[0] is True:
                    value = ""
                elif value[0] is False:
                    continue
                else:
                    value = " ".join(value)
            else:
                continue
            policy.append(f"{directive} {value}".strip())
        return "; ".join(policy)
