"this is the locale selecting middleware that will look at accept headers"

from django.utils.cache import patch_vary_headers
from django.utils import translation

# this is a cache that will build a map from modules to applications
_module_to_app = {}

class LocaleMiddleware:
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """

    def process_view(self, request, view_func, param_dict):
        global _module_to_app

        def findapp(module):
            app = _module_to_app.get(view_func.__module__, None)
            if app is not None:
                return app

            from django.conf import settings
            for app in settings.INSTALLED_APPS:
                if module.startswith(app):
                    _module_to_app[module] = app
                    return app
            return '*'

        app = findapp(view_func.__module__)

        lang = translation.get_language_from_request(request)

        translation.activate(app, lang)

        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        return response

