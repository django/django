"This is the locale selecting middleware that will look at accept headers"

from django.core.urlresolvers import get_resolver, LocaleRegexURLResolver
from django.http import HttpResponseRedirect
from django.utils.cache import patch_vary_headers
from django.utils import translation

class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """

    def process_request(self, request):
        language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        language = translation.get_language()
        translation.deactivate()

        if (response.status_code == 404 and
                not translation.get_language_from_path(request.path_info)
                    and self.is_language_prefix_patterns_used()):
            return HttpResponseRedirect(
                '/%s%s' % (language, request.get_full_path()))

        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = language
        return response

    def is_language_prefix_patterns_used(self):
        """
        Returns `True` if the `LocaleRegexURLResolver` is used
        at root level of the urlpatterns, else it returns `False`.
        """
        for url_pattern in get_resolver(None).url_patterns:
            if isinstance(url_pattern, LocaleRegexURLResolver):
                return True
        return False
