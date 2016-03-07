"This is the locale selecting middleware that will look at accept headers"

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import (
    LocaleRegexURLResolver, get_resolver, get_script_prefix, is_valid_path,
)
from django.utils import lru_cache, translation
from django.utils.cache import patch_vary_headers


class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """
    response_redirect_class = HttpResponseRedirect

    def process_request(self, request):
        urlconf = getattr(request, 'urlconf', settings.ROOT_URLCONF)
        language = translation.get_language_from_request(
            request, check_path=self.is_language_prefix_patterns_used(urlconf)
        )
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        language = translation.get_language()
        language_from_path = translation.get_language_from_path(request.path_info)
        urlconf = getattr(request, 'urlconf', settings.ROOT_URLCONF)
        if (response.status_code == 404 and not language_from_path
                and self.is_language_prefix_patterns_used(urlconf)):
            language_path = '/%s%s' % (language, request.path_info)
            path_valid = is_valid_path(language_path, urlconf)
            path_needs_slash = (
                not path_valid and (
                    settings.APPEND_SLASH and not language_path.endswith('/')
                    and is_valid_path('%s/' % language_path, urlconf)
                )
            )

            if path_valid or path_needs_slash:
                script_prefix = get_script_prefix()
                # Insert language after the script prefix and before the
                # rest of the URL
                language_url = request.get_full_path(force_append_slash=path_needs_slash).replace(
                    script_prefix,
                    '%s%s/' % (script_prefix, language),
                    1
                )
                return self.response_redirect_class(language_url)

        if not (self.is_language_prefix_patterns_used(urlconf)
                and language_from_path):
            patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = language
        return response

    @lru_cache.lru_cache(maxsize=None)
    def is_language_prefix_patterns_used(self, urlconf):
        """
        Returns `True` if the `LocaleRegexURLResolver` is used
        at root level of the urlpatterns, else it returns `False`.
        """
        for url_pattern in get_resolver(urlconf).url_patterns:
            if isinstance(url_pattern, LocaleRegexURLResolver):
                return True
        return False
