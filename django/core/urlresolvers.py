"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a tuple in this format:

    (view_function, dict_of_view_function_args)
"""

from django.core.exceptions import Http404, ViewDoesNotExist
import re

class Resolver404(Http404):
    pass

def get_mod_func(callback):
    # Converts 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    dot = callback.rindex('.')
    return callback[:dot], callback[dot+1:]

class RegexURLPattern:
    def __init__(self, regex, callback, default_args=None):
        # regex is a string representing a regular expression.
        # callback is something like 'foo.views.news.stories.story_detail',
        # which represents the path to a module and a view function name.
        self.regex = re.compile(regex)
        self.callback = callback
        self.default_args = default_args or {}

    def resolve(self, path):
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
        except ImportError, e:
            raise ViewDoesNotExist, "Could not import %s. Error was: %s" % (mod_name, str(e))
        except AttributeError, e:
            raise ViewDoesNotExist, "Tried %s in module %s. Error was: %s" % (func_name, mod_name, str(e))

class RegexURLResolver(object):
    def __init__(self, regex, urlconf_name):
        # regex is a string representing a regular expression.
        # urlconf_name is a string representing the module containing urlconfs.
        self.regex = re.compile(regex)
        self.urlconf_name = urlconf_name

    def resolve(self, path):
        tried = []
        match = self.regex.search(path)
        if match:
            new_path = path[match.end():]
            for pattern in self.urlconf_module.urlpatterns:
                try:
                    sub_match = pattern.resolve(new_path)
                except Resolver404, e:
                    tried.extend([(pattern.regex.pattern + '   ' + t) for t in e.args[0]['tried']])
                else:
                    if sub_match:
                        return sub_match[0], dict(match.groupdict(), **sub_match[1])
                    tried.append(pattern.regex.pattern)
            raise Resolver404, {'tried': tried, 'path': new_path}

    def _get_urlconf_module(self):
        try:
            return self._urlconf_module
        except AttributeError:
            self._urlconf_module = __import__(self.urlconf_name, '', '', [''])
            return self._urlconf_module
    urlconf_module = property(_get_urlconf_module)

    def _resolve_special(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type)
        mod_name, func_name = get_mod_func(callback)
        try:
            return getattr(__import__(mod_name, '', '', ['']), func_name), {}
        except (ImportError, AttributeError), e:
            raise ViewDoesNotExist, "Tried %s. Error was: %s" % (callback, str(e))

    def resolve404(self):
        return self._resolve_special('404')

    def resolve500(self):
        return self._resolve_special('500')
