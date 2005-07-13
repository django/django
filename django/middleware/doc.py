from django.conf import settings
from django.utils import httpwrappers

class XViewMiddleware:
    """
    Adds an X-View header to internal HEAD requests -- used by the documentation system.
    """

    def process_view(self, request, view_func, param_dict):
        """
        If the request method is HEAD and the IP is internal, quickly return
        with an x-header indicating the view function.  This is used by the
        documentation module to lookup the view function for an arbitrary page.
        """
        if request.META['REQUEST_METHOD'] == 'HEAD' and request.META['REMOTE_ADDR'] in settings.INTERNAL_IPS:
            response = httpwrappers.HttpResponse()
            response['X-View'] = "%s.%s" % (view_func.__module__, view_func.__name__)
            return response
