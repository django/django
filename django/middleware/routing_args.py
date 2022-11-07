__all__ = ("RoutingArgsMiddleware",)
from django.utils.deprecation import MiddlewareMixin


class RoutingArgsMiddleware(MiddlewareMixin):
    """
    Middleware that stores the view's positional and named arguments in the
    request.

    This implements the `wsgiorg.routing_args
    <http://wsgi.readthedocs.org/en/latest/specifications/routing_args.html>`_
    standard.

    This implementation is not complete because we would have to move
    a part of PATH_INFO to SCRIPT_NAME, which would break backwards
    compatibility. It's also incomplete because `Django does not
    support mixing positional and named arguments
    <http://docs.djangoproject.com/en/dev/topics/http/urls/#the-matching-grouping-algorithm>`_.

    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.environ["wsgiorg.routing_args"] = (
            view_args,
            view_kwargs.copy(),
        )
