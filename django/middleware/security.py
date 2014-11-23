import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect


def construct_csp_header(policy, report_only=False):
    """
    Construct Content Security Policy header from a dictonay with all the
    individual policy directives.
    Returns a tuple with the name and value of the header to be set.
    The value will be set to None for empty policies.
    """
    if not policy:
        return None

    name = ('content-security-policy-report-only'
            if report_only else 'content-security-policy')

    value = '; '.join(('{} {}'.format(k, v) for k, v in policy.items()))

    return {'name': name, 'value': value}


class SecurityMiddleware(object):
    def __init__(self):
        self.sts_seconds = settings.SECURE_HSTS_SECONDS
        self.sts_include_subdomains = settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        self.content_type_nosniff = settings.SECURE_CONTENT_TYPE_NOSNIFF
        self.xss_filter = settings.SECURE_BROWSER_XSS_FILTER
        self.redirect = settings.SECURE_SSL_REDIRECT
        self.redirect_host = settings.SECURE_SSL_HOST
        self.redirect_exempt = [re.compile(r) for r in settings.SECURE_REDIRECT_EXEMPT]
        self.csp = construct_csp_header(settings.SECURE_CSP, report_only=False)
        self.csp_report_only = construct_csp_header(
                settings.SECURE_CSP_REPORT_ONLY, report_only=True)

    def process_request(self, request):
        path = request.path.lstrip("/")
        if (self.redirect and not request.is_secure() and
                not any(pattern.search(path)
                        for pattern in self.redirect_exempt)):
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

            response["strict-transport-security"] = sts_header

        if self.content_type_nosniff and 'x-content-type-options' not in response:
            response["x-content-type-options"] = "nosniff"

        if self.xss_filter and 'x-xss-protection' not in response:
            response["x-xss-protection"] = "1; mode=block"

        csp_exempt = getattr(response, 'csp_exempt', False)

        if self.csp and not csp_exempt and not self.csp['name'] in response:
            response[self.csp['name']] = self.csp['value']

        if (self.csp_report_only and not csp_exempt and
                not self.csp_report_only['name'] in response):
            response[self.csp_report_only['name']] = self.csp_report_only['value']

        return response
