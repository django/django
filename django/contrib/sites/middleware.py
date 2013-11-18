from django.conf import settings
from django.contrib.sites.models import Site


class SiteMiddleware(object):
    """
    Middleware that sets `site` attribute to request object.
    """

    def process_request(self, request):
        request.site = Site.objects.get_current()
