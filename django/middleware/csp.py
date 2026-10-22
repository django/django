from django.conf import settings
from django.middleware import MiddlewareMixin
from django.utils.cache import patch_cache_control
from django.utils.csp import CSP, LazyNonce, _csp_policy_contains_nonce, build_policy


def get_nonce(request):
    return getattr(request, "_csp_nonce", None)


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    async_capable = False
    # Subclass and set to True if you handle nonce-safe caching yourself.
    nonce_caching_allowed = False

    def process_request(self, request):
        request._csp_nonce = LazyNonce()

    def process_response(self, request, response):
        nonce = get_nonce(request)

        sentinel = object()
        if (csp_config := getattr(response, "_csp_config", sentinel)) is sentinel:
            csp_config = settings.SECURE_CSP
        if (csp_ro_config := getattr(response, "_csp_ro_config", sentinel)) is sentinel:
            csp_ro_config = settings.SECURE_CSP_REPORT_ONLY

        policy_has_nonce = False
        for header, config in [
            (CSP.HEADER_ENFORCE, csp_config),
            (CSP.HEADER_REPORT_ONLY, csp_ro_config),
        ]:
            # If headers are already set on the response, don't overwrite them.
            # This allows for views to set their own CSP headers as needed.
            # An empty config means CSP headers are not added to the response.
            if config and header not in response:
                contains_nonce = nonce is not None and _csp_policy_contains_nonce(
                    config
                )
                if response.streaming and contains_nonce:
                    # Streaming content may first access the lazy nonce after
                    # the CSP header is built. Generate it now so the header
                    # includes the nonce used in the body.
                    str(nonce)
                response.headers[str(header)] = build_policy(config, nonce)
                policy_has_nonce |= contains_nonce

        # A nonce is single-use; don't let a shared cache replay it.
        if nonce and policy_has_nonce and not self.nonce_caching_allowed:
            patch_cache_control(response, private=True)

        return response
