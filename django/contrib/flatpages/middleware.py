from django.contrib.flatpages.views import flatpage
from django.conf.settings import DEBUG

class FlatpageFallbackMiddleware:
    def process_response(self, request, response):
        if response.status_code != 404:
            return response # No need to check for a flatpage for non-404 responses.
        try:
            return flatpage(request, request.path)
        # Return the original response if any errors happened. Because this
        # is a middleware, we can't assume the errors will be caught elsewhere.
        except:
            if DEBUG:
                raise
            return response
