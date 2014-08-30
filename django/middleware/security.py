import re

from django.http import HttpResponsePermanentRedirect

from django.conf import settings


class SecurityMiddleware(object):
    def __init__(self):
        self.sts_seconds = settings.SECURITY_MIDDLEWARE['HSTS_SECONDS']
        self.sts_include_subdomains = settings.SECURITY_MIDDLEWARE['HSTS_INCLUDE_SUBDOMAINS']
        self.content_type_nosniff = settings.SECURITY_MIDDLEWARE['CONTENT_TYPE_NOSNIFF']
        self.xss_filter = settings.SECURITY_MIDDLEWARE['BROWSER_XSS_FILTER']
        self.redirect = settings.SECURITY_MIDDLEWARE['SSL_REDIRECT']
        self.redirect_host = settings.SECURITY_MIDDLEWARE['SSL_HOST']
        self.redirect_exempt = [
            re.compile(r) for r in settings.SECURITY_MIDDLEWARE['REDIRECT_EXEMPT']]

    def process_request(self, request):
        path = request.path.lstrip("/")
        if (self.redirect and
                not request.is_secure() and
                not any(pattern.search(path)
                        for pattern in self.redirect_exempt)):
            host = self.redirect_host or request.get_host()
            return HttpResponsePermanentRedirect(
                "https://%s%s" % (host, request.get_full_path()))

    def process_response(self, request, response):
        if (self.sts_seconds and
                request.is_secure() and
                'strict-transport-security' not in response):
            sts_header = ("max-age=%s" % self.sts_seconds)

            if self.sts_include_subdomains:
                sts_header = sts_header + "; includeSubDomains"

            response["strict-transport-security"] = sts_header

        if (self.content_type_nosniff and
                'x-content-type-options' not in response):
            response["x-content-type-options"] = "nosniff"

        if self.xss_filter and 'x-xss-protection' not in response:
            response["x-xss-protection"] = "1; mode=block"

        return response
