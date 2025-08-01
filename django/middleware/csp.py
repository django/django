from django.conf import settings
from django.utils.csp import CSP, LazyNonce, build_policy
from django.utils.deprecation import MiddlewareMixin


def get_nonce(request):
    return getattr(request, "_csp_nonce", None)


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._csp_nonce = LazyNonce()

    def process_response(self, request, response):
        nonce = get_nonce(request)
        for config, header, disabled in [
            (
                getattr(response, "_csp_config", None) or settings.SECURE_CSP,
                CSP.HEADER_ENFORCE,
                getattr(response, "_csp_disabled", False),
            ),
            (
                getattr(response, "_csp_config_ro", None)
                or settings.SECURE_CSP_REPORT_ONLY,
                CSP.HEADER_REPORT_ONLY,
                getattr(response, "_csp_disabled_ro", False),
            ),
        ]:
            # Only set CSP headers if they are not present on the response,
            # and if CSP is not disabled via the `@csp_disabled` decorator.
            # This allows views to customize or disable CSP headers as needed.
            if config and header not in response and not disabled:
                response.headers[str(header)] = build_policy(config, nonce)

        return response
