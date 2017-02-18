from .shortcuts import get_current_site


class CurrentSiteMiddleware(object):
    """
    Middleware that sets `site` attribute to request object.
    """

    def process_request(self, request):
        request.site = get_current_site(request)
