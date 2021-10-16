from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.redirects.models import Redirect
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.http import (
    HttpResponseGone, HttpResponsePermanentRedirect, HttpResponseRedirect,
)
from django.utils.deprecation import MiddlewareMixin


class RedirectFallbackMiddleware(MiddlewareMixin):
    # Defined as class-level attribute to be subclassing-friendly.
    redirect_model_class = Redirect
    response_redirect_types = {
        301: HttpResponsePermanentRedirect,
        302: HttpResponseRedirect,
        410: HttpResponseGone
    }

    def __init__(self, get_response):
        if not apps.is_installed('django.contrib.sites'):
            raise ImproperlyConfigured(
                "You cannot use RedirectFallbackMiddleware when "
                "django.contrib.sites is not installed."
            )
        super().__init__(get_response)

    def get_response_redirect_types(self):
        return self.response_redirect_types

    def process_response(self, request, response):
        # No need to check for a redirect for non-404 responses.
        if response.status_code != 404:
            return response

        append_slash = (
            settings.APPEND_SLASH and
            not Path(request.path).suffix and
            not request.path.endswith('/')
        )
        full_path = request.get_full_path(force_append_slash=append_slash)
        current_site = get_current_site(request)

        try:
            r = self.redirect_model_class.objects.get(
                site=current_site, old_path=full_path
            )
        except self.redirect_model_class.DoesNotExist:
            pass
        else:
            response_redirect_class = self.get_response_redirect_types().get(r.redirect_type)
            if response_redirect_class:
                if r.redirect_type == 410:
                    return response_redirect_class()
                return response_redirect_class(r.new_path)

        # No redirect or redirect type was found. Return the response.
        return response
