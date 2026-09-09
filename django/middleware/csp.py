from django.conf import settings
from django.middleware import MiddlewareMixin
from django.utils.cache import patch_cache_control
from django.utils.csp import CSP, LazyNonce, build_policy


def get_nonce(request):
    return getattr(request, "_csp_nonce", None)


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    # Subclass and set to False if you handle nonce-safe caching yourself.
    nonce_cache_control = True

    def process_request(self, request):
        request._csp_nonce = LazyNonce()

    def process_response(self, request, response):
        nonce = get_nonce(request)

        sentinel = object()
        if (csp_config := getattr(response, "_csp_config", sentinel)) is sentinel:
            csp_config = settings.SECURE_CSP
        if (csp_ro_config := getattr(response, "_csp_ro_config", sentinel)) is sentinel:
            csp_ro_config = settings.SECURE_CSP_REPORT_ONLY

        for header, config in [
            (CSP.HEADER_ENFORCE, csp_config),
            (CSP.HEADER_REPORT_ONLY, csp_ro_config),
        ]:
            # If headers are already set on the response, don't overwrite them.
            # This allows for views to set their own CSP headers as needed.
            # An empty config means CSP headers are not added to the response.
            if config and header not in response:
                response.headers[str(header)] = build_policy(config, nonce)

        # A nonce is single-use; don't let a shared cache replay it.
        if nonce and self.nonce_cache_control:
            patch_cache_control(response, private=True)

        return response
