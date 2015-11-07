from django.conf import settings
from django.contrib.flatpages.views import flatpage
from django.http import Http404
from django.middleware.exception import ExceptionMiddleware


class FlatpageFallbackMiddleware(ExceptionMiddleware):

    def __init__(self, get_response=None):
        # This override makes get_response optional during the
        # MIDDLEWARE_CLASSES deprecation.
        super(FlatpageFallbackMiddleware, self).__init__(get_response)

    def __call__(self, request):
        response = super(FlatpageFallbackMiddleware, self).__call__(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        if response.status_code != 404:
            return response  # No need to check for a flatpage for non-404 responses.
        try:
            return flatpage(request, request.path_info)
        # Return the original response if any errors happened. Because this
        # is a middleware, we can't assume the errors will be caught elsewhere.
        except Http404:
            return response
        except Exception:
            if settings.DEBUG:
                raise
            return response
