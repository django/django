from django.contrib.redirects.models import Redirect
from django import http
from django.conf import settings

class RedirectFallbackMiddleware:
    def process_response(self, request, response):
        if response.status_code != 404:
            return response # No need to check for a redirect for non-404 responses.
        path = request.get_full_path()
        try:
            r = Redirect.objects.get(site__id__exact=settings.SITE_ID, old_path=path)
        except Redirect.DoesNotExist:
            r = None
        if r is None and settings.APPEND_SLASH:
            # Try removing the trailing slash.
            try:
                r = Redirect.objects.get(site__id__exact=settings.SITE_ID,
                    old_path=path[:path.rfind('/')]+path[path.rfind('/')+1:])
            except Redirect.DoesNotExist:
                pass
        if r is not None:
            if r == '':
                return http.HttpResponseGone()
            return http.HttpResponsePermanentRedirect(r.new_path)

        # No redirect was found. Return the response.
        return response
