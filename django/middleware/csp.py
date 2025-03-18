import base64
import os
from functools import partial
from http import client as http_client

from django.conf import csp, settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

HEADER = "Content-Security-Policy"
HEADER_REPORT_ONLY = "Content-Security-Policy-Report-Only"


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    @staticmethod
    def _make_nonce(request):
        # Ensure that any subsequent calls to request.csp_nonce return the same value
        if not getattr(request, "_csp_nonce", None):
            request._csp_nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        return request._csp_nonce

    def process_request(self, request):
        request.csp_nonce = SimpleLazyObject(partial(self._make_nonce, request))

    def process_response(self, request, response):
        # In DEBUG mode, exclude CSP headers for specific status codes that
        # trigger the debug view.
        exempted_status_codes = {
            http_client.NOT_FOUND,
            http_client.INTERNAL_SERVER_ERROR,
        }
        if settings.DEBUG and response.status_code in exempted_status_codes:
            return response

        # If headers are already set on the response, don't overwrite them.
        # This allows for views to set their own CSP headers as needed.
        no_csp_header = HEADER not in response
        is_not_disabled = not getattr(response, "_csp_disabled", False)
        if no_csp_header and is_not_disabled:
            config, nonce = self.get_policy(request, response)
            if config:
                response.headers[HEADER] = self.build_policy(config, nonce)

        no_csp_header = HEADER_REPORT_ONLY not in response
        is_not_disabled = not getattr(response, "_csp_disabled_ro", False)
        if no_csp_header and is_not_disabled:
            config, nonce = self.get_policy(request, response, report_only=True)
            if config:
                response.headers[HEADER_REPORT_ONLY] = self.build_policy(config, nonce)

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
        nonce = getattr(request, "_csp_nonce", None)
        return (config, nonce)

    # TODO: Make this cache-able?
    # This is challenging due to:
    # - Having the nonce, which is unique per request
    # - The decorators pass in their own configs
    @staticmethod
    def build_policy(config, nonce=None):
        policy = []
        directives = config.get("DIRECTIVES", {})

        for directive, value in directives.items():
            if value is None:
                continue
            if not isinstance(value, list | tuple):
                value = [value]
            if csp.NONCE in value:
                if nonce:
                    value = [f"'nonce-{nonce}'" if v == csp.NONCE else v for v in value]
                else:
                    # Remove the `NONCE` sentinel value if no nonce is provided.
                    value = [v for v in value if v != csp.NONCE]
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
