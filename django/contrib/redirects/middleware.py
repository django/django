from __future__ import unicode_literals

from django.conf import settings
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django import http


class RedirectFallbackMiddleware(object):
    def __init__(self):
        if 'django.contrib.sites' not in settings.INSTALLED_APPS:
            raise ImproperlyConfigured(
                "You cannot use RedirectFallbackMiddleware when "
                "django.contrib.sites is not installed."
            )

    def process_response(self, request, response):
        if response.status_code != 404:
            return response # No need to check for a redirect for non-404 responses.

        full_path = request.get_full_path()
        current_site = get_current_site(request)

        r = None
        try:
            r = Redirect.objects.get(site=current_site, old_path=full_path)
        except Redirect.DoesNotExist:
            pass
        if settings.APPEND_SLASH and not request.path.endswith('/'):
            # Try appending a trailing slash.
            path_len = len(request.path)
            full_path = full_path[:path_len] + '/' + full_path[path_len:]
            try:
                r = Redirect.objects.get(site=current_site, old_path=full_path)
            except Redirect.DoesNotExist:
                pass
        if r is not None:
            if r.new_path == '':
                return http.HttpResponseGone()
            return http.HttpResponsePermanentRedirect(r.new_path)

        # No redirect was found. Return the response.
        return response
