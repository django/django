import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin


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
        self.csp = settings.SECURE_CSP
        self.csp_multiple = settings.SECURE_CSP_MULTIPLE
        self.csp_report_only = settings.SECURE_CSP_REPORT_ONLY
        self.csp_nonce = settings.SECURE_CSP_INCLUDE_NONCE_IN
        self.csp_exclude_url_prefixes = settings.SECURE_CSP_EXCLUDE_URL_PREFIXES

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

        if request.path_info.startswith(self.csp_exclude_url_prefixes):
            return response

        if self.csp:
            header = "Content-Security-Policy"
            csp_header_value = "; ".join((f"{k} {v}" for k, v in self.csp.items()))

            if self.csp_report_only:
                header += "-Report-Only"

            if self.csp_nonce:
                nonce = getattr(request, "_csp_nonce", None)
                csp_header_value += "; 'nonce-%s'" % nonce
            response.headers[header] = csp_header_value

        if self.csp_multiple:
            # Support a comma-separated string or iterable of values to allow
            # fallback.
            header = "Content-Security-Policy"
            csp_header_value = "; ".join(
                [v.strip() for v in self.csp_multiple.split(";")]
                if isinstance(self.csp_multiple, str)
                else self.csp_multiple
            )
            if self.csp_report_only:
                header += "-Report-Only"
            response.headers[header] = csp_header_value

        return response
