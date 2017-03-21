from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class XViewMiddleware(MiddlewareMixin):
    """
    Add an X-View header to internal HEAD requests.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        If the request method is HEAD and either the IP is internal or the
        user is a logged-in staff member, return a responsewith an x-view
        header indicating the view function. This is used to lookup the view
        function for an arbitrary page.
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
            response = HttpResponse()
            response['X-View'] = "%s.%s" % (view_func.__module__, view_func.__name__)
            return response
