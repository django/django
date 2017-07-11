import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin


class SecurityMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.sts_seconds = settings.SECURE_HSTS_SECONDS
        self.sts_include_subdomains = settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        self.sts_preload = settings.SECURE_HSTS_PRELOAD
        self.content_type_nosniff = settings.SECURE_CONTENT_TYPE_NOSNIFF
        self.xss_filter = settings.SECURE_BROWSER_XSS_FILTER
        self.redirect = settings.SECURE_SSL_REDIRECT
        self.redirect_host = settings.SECURE_SSL_HOST
        self.redirect_exempt = [re.compile(r) for r in settings.SECURE_REDIRECT_EXEMPT]
        self.get_response = get_response

    def process_request(self, request):
        if not self.redirect:
            return
        if (request.is_secure() and (
                # redirect_host is not set OR
                not self.redirect_host or
                # host is already the same
                self.redirect_host == request.get_host())):
            return
        path = request.path.lstrip("/")
        if any(pattern.search(path) for pattern in self.redirect_exempt):
            return

        host = self.redirect_host or request.get_host()
        return HttpResponsePermanentRedirect(
            "https://%s%s" % (host, request.get_full_path())
        )

    def process_response(self, request, response):
        if (self.sts_seconds and request.is_secure() and
                'strict-transport-security' not in response):
            sts_header = "max-age=%s" % self.sts_seconds
            if self.sts_include_subdomains:
                sts_header = sts_header + "; includeSubDomains"
            if self.sts_preload:
                sts_header = sts_header + "; preload"
            response["strict-transport-security"] = sts_header

        if self.content_type_nosniff and 'x-content-type-options' not in response:
            response["x-content-type-options"] = "nosniff"

        if self.xss_filter and 'x-xss-protection' not in response:
            response["x-xss-protection"] = "1; mode=block"

        return response
