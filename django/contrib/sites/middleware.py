from django.utils.cache import patch_vary_headers

from .shortcuts import get_current_site


class CurrentSiteMiddleware(object):
    """
    Middleware that sets `site` attribute to request object.
    """

    def process_request(self, request):
        request.site = get_current_site(request)
        if request.site and request.site.urlconf:
            request.urlconf = request.site.urlconf

    def process_response(self, request, response):
        if hasattr(request, 'urlconf'):
            patch_vary_headers(response, ['Host'])
        return response
