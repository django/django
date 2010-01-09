from django.conf import settings
from django import http

class XViewMiddleware(object):
    """
    Adds an X-View header to internal HEAD requests -- used by the documentation system.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        If the request method is HEAD and either the IP is internal or the
        user is a logged-in staff member, quickly return with an x-header
        indicating the view function.  This is used by the documentation module
        to lookup the view function for an arbitrary page.
        """
        if request.method == 'HEAD' and (request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS or request.user.is_staff):
            response = http.HttpResponse()
            response['X-View'] = "%s.%s" % (view_func.__module__, view_func.__name__)
            return response
