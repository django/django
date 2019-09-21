from .shortcuts import get_current_site


class CurrentSiteMiddleware:
    """
    Middleware that sets `site` attribute to request object.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.site = get_current_site(request)
        return self.get_response(request)
