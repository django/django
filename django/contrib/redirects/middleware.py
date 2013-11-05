from __future__ import unicode_literals

from django.conf import settings
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django import http


class RedirectFallbackMiddleware(object):

    # Defined as class-level attributes to be subclassing-friendly.
    response_gone_class = http.HttpResponseGone
    response_redirect_class = http.HttpResponsePermanentRedirect

    def process_response(self, request, response):
        # No need to check for a redirect for non-404 responses.
        if response.status_code != 404:
            return response

        path = request.path
        full_path = request.get_full_path()

        redirects = Redirect.objects
        if Site._meta.installed:
            redirects = redirects.filter(site=Site.objects.get_current())

        r = None

        try:
            r = redirects.get(old_path=full_path)
        except Redirect.DoesNotExist:
            pass

        if settings.APPEND_SLASH and not path.endswith('/'):
            # Try appending a trailing slash.
            path_len = len(path)
            full_path = full_path[:path_len] + '/' + full_path[path_len:]
            try:
                r = redirects.get(old_path=full_path)
            except Redirect.DoesNotExist:
                pass

        if r is not None:
            if r.new_path == '':
                return self.response_gone_class()
            return self.response_redirect_class(r.new_path)

        # No redirect was found. Return the response.
        return response
