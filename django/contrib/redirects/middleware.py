from django.models.redirects import redirects
from django.utils import httpwrappers
from django.conf.settings import APPEND_SLASH, SITE_ID

class RedirectFallbackMiddleware:
    def process_response(self, request, response):
        if response.status_code != 404:
            return response # No need to check for a redirect for non-404 responses.
        path = request.get_full_path()
        try:
            r = redirects.get_object(site__id__exact=SITE_ID, old_path__exact=path)
        except redirects.RedirectDoesNotExist:
            r = None
        if r is None and APPEND_SLASH:
            # Try removing the trailing slash.
            try:
                r = redirects.get_object(site__id__exact=SITE_ID,
                    old_path__exact=path[:path.rfind('/')]+path[path.rfind('/')+1:])
            except redirects.RedirectDoesNotExist:
                pass
        if r is not None:
            if r == '':
                return httpwrappers.HttpResponseGone()
            return httpwrappers.HttpResponsePermanentRedirect(r.new_path)

        # No redirect was found. Return the response.
        return response
