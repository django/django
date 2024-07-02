import base64
import os
import re
from functools import partial

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.middleware.constants import csp
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

# TODO: Consider adding constants for the various CSP directive values such as `'self'`,
# `'unsafe-inline'`, `'unsafe-eval'`, etc.  This could help prevent typos and quoting
# errors and make it easier to see what values are allowed.

# TODO: Consider adding support for CSP hash sources, similar to nonce sources.

# TODO: Consider adding a context processor to make the CSP nonce available in
# templates.  This could be useful to add the nonce to inline scripts, styles, etc.


def build_csp(config, nonce=None):
    policy = []
    directives = config.get("DIRECTIVES", {})

    for directive, value in directives.items():
        if value is None:
            continue
        if not isinstance(value, (list, tuple)):
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


class SecurityMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.sts_seconds = settings.SECURE_HSTS_SECONDS
        self.sts_include_subdomains = settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        self.sts_preload = settings.SECURE_HSTS_PRELOAD
        self.content_type_nosniff = settings.SECURE_CONTENT_TYPE_NOSNIFF
        self.redirect = settings.SECURE_SSL_REDIRECT
        self.redirect_host = settings.SECURE_SSL_HOST
        self.redirect_exempt = [re.compile(r) for r in settings.SECURE_REDIRECT_EXEMPT]
        self.referrer_policy = settings.SECURE_REFERRER_POLICY
        self.cross_origin_opener_policy = settings.SECURE_CROSS_ORIGIN_OPENER_POLICY
        # TODO: Confirm this is the best place for CSP to live.
        self.csp = settings.SECURE_CSP
        self.csp_report_only = settings.SECURE_CSP_REPORT_ONLY

    def _make_nonce(self, request):
        # Ensure that any subsequent calls to request.csp_nonce return the same value
        if not getattr(request, "_csp_nonce", None):
            request._csp_nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        return request._csp_nonce

    def process_request(self, request):
        path = request.path.lstrip("/")
        if (
            self.redirect
            and not request.is_secure()
            and not any(pattern.search(path) for pattern in self.redirect_exempt)
        ):
            host = self.redirect_host or request.get_host()
            return HttpResponsePermanentRedirect(
                "https://%s%s" % (host, request.get_full_path())
            )
        nonce = partial(self._make_nonce, request)
        request.csp_nonce = SimpleLazyObject(nonce)

    def process_response(self, request, response):
        if (
            self.sts_seconds
            and request.is_secure()
            and "Strict-Transport-Security" not in response
        ):
            sts_header = "max-age=%s" % self.sts_seconds
            if self.sts_include_subdomains:
                sts_header += "; includeSubDomains"
            if self.sts_preload:
                sts_header += "; preload"
            response.headers["Strict-Transport-Security"] = sts_header

        if self.content_type_nosniff:
            response.headers.setdefault("X-Content-Type-Options", "nosniff")

        if self.referrer_policy:
            # Support a comma-separated string or iterable of values to allow
            # fallback.
            response.headers.setdefault(
                "Referrer-Policy",
                ",".join(
                    [v.strip() for v in self.referrer_policy.split(",")]
                    if isinstance(self.referrer_policy, str)
                    else self.referrer_policy
                ),
            )

        if self.cross_origin_opener_policy:
            response.setdefault(
                "Cross-Origin-Opener-Policy",
                self.cross_origin_opener_policy,
            )

        # TODO: Consider if we want to exclude CSP from a default set of views in
        # DEBUG mode, similar to django-csp.
        # TODO: Consider if we want to ship with the `@csp_exempt` decorator, to exclude
        # views from CSP headers.
        # TODO: Consider if we want to allow per-view configuration of CSP headers via
        # decorators, similar to django-csp.

        # If headers are already set on the response, don't overwrite them.
        # This allows for views to set their own CSP headers as needed.
        if self.csp and csp.HEADER not in response:
            response.headers[csp.HEADER] = build_csp(self.csp, nonce=request.csp_nonce)

        if self.csp_report_only and csp.HEADER_REPORT_ONLY not in response:
            response.headers[csp.HEADER_REPORT_ONLY] = build_csp(
                self.csp_report_only, nonce=request.csp_nonce
            )

        return response
