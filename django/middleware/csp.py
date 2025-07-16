from http import HTTPStatus

from django.conf import settings
from django.utils.csp import CSP, LazyNonce, build_policy
from django.utils.deprecation import MiddlewareMixin


def get_nonce(request):
    return getattr(request, "_csp_nonce", None)


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._csp_nonce = LazyNonce()

    def process_response(self, request, response):
        # In DEBUG mode, exclude CSP headers for specific status codes that
        # trigger the debug view.
        exempted_status_codes = {
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
        }
        if settings.DEBUG and response.status_code in exempted_status_codes:
            return response

        nonce = get_nonce(request)
        for header, config in [
            (CSP.HEADER_ENFORCE, settings.SECURE_CSP),
            (CSP.HEADER_REPORT_ONLY, settings.SECURE_CSP_REPORT_ONLY),
        ]:
            # If headers are already set on the response, don't overwrite them.
            # This allows for views to set their own CSP headers as needed.
            if config and header not in response:
                response.headers[str(header)] = build_policy(config, nonce)

        return response
