from django import http
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .utils import get_view_name


class XViewMiddleware(MiddlewareMixin):
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
        assert hasattr(request, 'user'), (
            "The XView middleware requires authentication middleware to be "
            "installed. Edit your MIDDLEWARE%s setting to insert "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'." % (
                "_CLASSES" if settings.MIDDLEWARE is None else ""
            )
        )
        if request.method == 'HEAD' and (request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS or
                                         (request.user.is_active and request.user.is_staff)):
            response = http.HttpResponse()
            response['X-View'] = get_view_name(view_func)
            return response
