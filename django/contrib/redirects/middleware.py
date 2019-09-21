from django.apps import apps
from django.conf import settings
from django.contrib.redirects.models import Redirect
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseGone, HttpResponsePermanentRedirect


class RedirectFallbackMiddleware:
    # Defined as class-level attributes to be subclassing-friendly.
    response_gone_class = HttpResponseGone
    response_redirect_class = HttpResponsePermanentRedirect

    def __init__(self, get_response):
        if not apps.is_installed('django.contrib.sites'):
            raise ImproperlyConfigured(
                "You cannot use RedirectFallbackMiddleware when "
                "django.contrib.sites is not installed."
            )
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        # No need to check for a redirect for non-404 responses.
        if response.status_code != 404:
            return response

        full_path = request.get_full_path()
        current_site = get_current_site(request)

        r = None
        try:
            r = Redirect.objects.get(site=current_site, old_path=full_path)
        except Redirect.DoesNotExist:
            pass
        if r is None and settings.APPEND_SLASH and not request.path.endswith('/'):
            try:
                r = Redirect.objects.get(
                    site=current_site,
                    old_path=request.get_full_path(force_append_slash=True),
                )
            except Redirect.DoesNotExist:
                pass
        if r is not None:
            if r.new_path == '':
                return self.response_gone_class()
            return self.response_redirect_class(r.new_path)

        # No redirect was found. Return the response.
        return response
