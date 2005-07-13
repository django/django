"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a tuple in this format:

    (view_function, dict_of_view_function_args)
"""

from django.core.exceptions import Http404, ViewDoesNotExist
import re

def get_mod_func(callback):
    # Converts 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    dot = callback.rindex('.')
    return callback[:dot], callback[dot+1:]

class RegexURLPattern:
    def __init__(self, regex, callback, default_args=None):
        self.regex = re.compile(regex)
        # callback is something like 'foo.views.news.stories.story_detail',
        # which represents the path to a module and a view function name.
        self.callback = callback
        self.default_args = default_args or {}

    def search(self, path):
        match = self.regex.search(path)
        if match:
            args = dict(match.groupdict(), **self.default_args)
            try: # Lazily load self.func.
                return self.func, args
            except AttributeError:
                self.func = self.get_callback()
            return self.func, args

    def get_callback(self):
        mod_name, func_name = get_mod_func(self.callback)
        try:
            return getattr(__import__(mod_name, '', '', ['']), func_name)
        except (ImportError, AttributeError):
            raise ViewDoesNotExist, self.callback

class RegexURLMultiplePattern:
    def __init__(self, regex, urlconf_module):
        self.regex = re.compile(regex)
        # urlconf_module is a string representing the module containing urlconfs.
        self.urlconf_module = urlconf_module

    def search(self, path):
        match = self.regex.search(path)
        if match:
            new_path = path[match.end():]
            try: # Lazily load self.url_patterns.
                self.url_patterns
            except AttributeError:
                self.url_patterns = self.get_url_patterns()
            for pattern in self.url_patterns:
                sub_match = pattern.search(new_path)
                if sub_match:
                    return sub_match

    def get_url_patterns(self):
        return __import__(self.urlconf_module, '', '', ['']).urlpatterns

class RegexURLResolver:
    def __init__(self, url_patterns):
        # url_patterns is a list of RegexURLPattern or RegexURLMultiplePattern objects.
        self.url_patterns = url_patterns

    def resolve(self, app_path):
        # app_path is the full requested Web path. This is assumed to have a
        # leading slash but doesn't necessarily have a trailing slash.
        # Examples:
        #     "/news/2005/may/"
        #     "/news/"
        #     "/polls/latest"
        # A home (root) page is represented by "/".
        app_path = app_path[1:] # Trim leading slash.
        for pattern in self.url_patterns:
            match = pattern.search(app_path)
            if match:
                return match
        # None of the regexes matched, so raise a 404.
        raise Http404, app_path

class Error404Resolver:
    def __init__(self, callback):
        self.callback = callback

    def resolve(self):
        mod_name, func_name = get_mod_func(self.callback)
        try:
            return getattr(__import__(mod_name, '', '', ['']), func_name), {}
        except (ImportError, AttributeError):
            raise ViewDoesNotExist, self.callback
