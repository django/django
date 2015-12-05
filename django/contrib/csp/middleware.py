from django.conf import settings
from django.utils.six.moves import http_client

from csp.utils import build_policy


class CSPMiddleware(object):
    """
    Implements the Content-Security-Policy response header, which
    conforming user-agents can use to restrict the permitted sources
    of various content.

    See http://www.w3.org/TR/CSP/

    """

    def process_response(self, request, response):
        if getattr(response, '_csp_exempt', False):
            return response

        # Check for ignored path prefix.
        prefixes = getattr(settings, 'CSP_EXCLUDE_URL_PREFIXES', ('/admin',))
        if request.path_info.startswith(prefixes):
            return response

        # Check for debug view
        status_code = response.status_code
        if status_code == http_client.INTERNAL_SERVER_ERROR and settings.DEBUG:
            return response

        header = 'Content-Security-Policy'
        if getattr(settings, 'CSP_REPORT_ONLY', False):
            header += '-Report-Only'

        if header in response:
            # Don't overwrite existing headers.
            return response

        config = getattr(response, '_csp_config', None)
        update = getattr(response, '_csp_update', None)
        replace = getattr(response, '_csp_replace', None)
        response[header] = build_policy(config=config, update=update,
                                        replace=replace)
        return response
