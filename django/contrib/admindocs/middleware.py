from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .utils import get_view_name


class XViewMiddleware(MiddlewareMixin):
    """
    Add an X-View header to internal HEAD requests.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        If the request method is HEAD and either the IP is internal or the
        user is a logged-in staff member, return a response with an x-view
        header indicating the view function. This is used to lookup the view
        function for an arbitrary page.
        """
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The XView middleware requires authentication middleware to "
                "be installed. Edit your MIDDLEWARE setting to insert "
                "'django.contrib.auth.middleware.AuthenticationMiddleware'."
            )
        if request.method == 'HEAD' and (request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS or
                                         (request.user.is_active and request.user.is_staff)):
            response = HttpResponse()
            response.headers['X-View'] = get_view_name(view_func)
            return response
