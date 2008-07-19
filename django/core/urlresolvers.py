"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a tuple in this format:

    (view_function, function_args, function_kwargs)
"""

from django.http import Http404
from django.core.exceptions import ImproperlyConfigured, ViewDoesNotExist
from django.utils.encoding import iri_to_uri, force_unicode, smart_str
from django.utils.functional import memoize
import re

try:
    reversed
except NameError:
    from django.utils.itercompat import reversed     # Python 2.3 fallback

_resolver_cache = {} # Maps urlconf modules to RegexURLResolver instances.
_callable_cache = {} # Maps view and url pattern names to their view functions.

class Resolver404(Http404):
    pass

class NoReverseMatch(Exception):
    # Don't make this raise an error when used in a template.
    silent_variable_failure = True

def get_callable(lookup_view, can_fail=False):
    """
    Convert a string version of a function name to the callable object.

    If the lookup_view is not an import path, it is assumed to be a URL pattern
    label and the original string is returned.

    If can_fail is True, lookup_view might be a URL pattern label, so errors
    during the import fail and the string is returned.
    """
    if not callable(lookup_view):
        try:
            # Bail early for non-ASCII strings (they can't be functions).
            lookup_view = lookup_view.encode('ascii')
            mod_name, func_name = get_mod_func(lookup_view)
            if func_name != '':
                lookup_view = getattr(__import__(mod_name, {}, {}, ['']), func_name)
        except (ImportError, AttributeError):
            if not can_fail:
                raise
        except UnicodeEncodeError:
            pass
    return lookup_view
get_callable = memoize(get_callable, _callable_cache, 1)

def get_resolver(urlconf):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return RegexURLResolver(r'^/', urlconf)
get_resolver = memoize(get_resolver, _resolver_cache, 1)

def get_mod_func(callback):
    # Converts 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot+1:]

def reverse_helper(regex, *args, **kwargs):
    """
    Does a "reverse" lookup -- returns the URL for the given args/kwargs.
    The args/kwargs are applied to the given compiled regular expression.
    For example:

        >>> reverse_helper(re.compile('^places/(\d+)/$'), 3)
        'places/3/'
        >>> reverse_helper(re.compile('^places/(?P<id>\d+)/$'), id=3)
        'places/3/'
        >>> reverse_helper(re.compile('^people/(?P<state>\w\w)/(\w+)/$'), 'adrian', state='il')
        'people/il/adrian/'

    Raises NoReverseMatch if the args/kwargs aren't valid for the regex.
    """
    # TODO: Handle nested parenthesis in the following regex.
    result = re.sub(r'\(([^)]+)\)', MatchChecker(args, kwargs), regex.pattern)
    return result.replace('^', '').replace('$', '').replace('\\', '')

class MatchChecker(object):
    "Class used in reverse RegexURLPattern lookup."
    def __init__(self, args, kwargs):
        self.args, self.kwargs = args, kwargs
        self.current_arg = 0

    def __call__(self, match_obj):
        # match_obj.group(1) is the contents of the parenthesis.
        # First we need to figure out whether it's a named or unnamed group.
        #
        grouped = match_obj.group(1)
        m = re.search(r'^\?P<(\w+)>(.*?)$', grouped, re.UNICODE)
        if m: # If this was a named group...
            # m.group(1) is the name of the group
            # m.group(2) is the regex.
            try:
                value = self.kwargs[m.group(1)]
            except KeyError:
                # It was a named group, but the arg was passed in as a
                # positional arg or not at all.
                try:
                    value = self.args[self.current_arg]
                    self.current_arg += 1
                except IndexError:
                    # The arg wasn't passed in.
                    raise NoReverseMatch('Not enough positional arguments passed in')
            test_regex = m.group(2)
        else: # Otherwise, this was a positional (unnamed) group.
            try:
                value = self.args[self.current_arg]
                self.current_arg += 1
            except IndexError:
                # The arg wasn't passed in.
                raise NoReverseMatch('Not enough positional arguments passed in')
            test_regex = grouped
        # Note we're using re.match here on purpose because the start of
        # to string needs to match.
        if not re.match(test_regex + '$', force_unicode(value), re.UNICODE):
            raise NoReverseMatch("Value %r didn't match regular expression %r" % (value, test_regex))
        return force_unicode(value)

class RegexURLPattern(object):
    def __init__(self, regex, callback, default_args=None, name=None):
        # regex is a string representing a regular expression.
        # callback is either a string like 'foo.views.news.stories.story_detail'
        # which represents the path to a module and a view function name, or a
        # callable object (view).
        self.regex = re.compile(regex, re.UNICODE)
        if callable(callback):
            self._callback = callback
        else:
            self._callback = None
            self._callback_str = callback
        self.default_args = default_args or {}
        self.name = name

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.name, self.regex.pattern)

    def add_prefix(self, prefix):
        """
        Adds the prefix string to a string-based callback.
        """
        if not prefix or not hasattr(self, '_callback_str'):
            return
        self._callback_str = prefix + '.' + self._callback_str

    def resolve(self, path):
        match = self.regex.search(path)
        if match:
            # If there are any named groups, use those as kwargs, ignoring
            # non-named groups. Otherwise, pass all non-named arguments as
            # positional arguments.
            kwargs = match.groupdict()
            if kwargs:
                args = ()
            else:
                args = match.groups()
            # In both cases, pass any extra_kwargs as **kwargs.
            kwargs.update(self.default_args)

            return self.callback, args, kwargs

    def _get_callback(self):
        if self._callback is not None:
            return self._callback
        try:
            self._callback = get_callable(self._callback_str)
        except ImportError, e:
            mod_name, _ = get_mod_func(self._callback_str)
            raise ViewDoesNotExist, "Could not import %s. Error was: %s" % (mod_name, str(e))
        except AttributeError, e:
            mod_name, func_name = get_mod_func(self._callback_str)
            raise ViewDoesNotExist, "Tried %s in module %s. Error was: %s" % (func_name, mod_name, str(e))
        return self._callback
    callback = property(_get_callback)

    def reverse(self, viewname, *args, **kwargs):
        mod_name, func_name = get_mod_func(viewname)
        try:
            lookup_view = getattr(__import__(mod_name, {}, {}, ['']), func_name)
        except (ImportError, AttributeError):
            raise NoReverseMatch
        if lookup_view != self.callback:
            raise NoReverseMatch
        return self.reverse_helper(*args, **kwargs)

    def reverse_helper(self, *args, **kwargs):
        return reverse_helper(self.regex, *args, **kwargs)

class RegexURLResolver(object):
    def __init__(self, regex, urlconf_name, default_kwargs=None):
        # regex is a string representing a regular expression.
        # urlconf_name is a string representing the module containing urlconfs.
        self.regex = re.compile(regex, re.UNICODE)
        self.urlconf_name = urlconf_name
        self.callback = None
        self.default_kwargs = default_kwargs or {}
        self._reverse_dict = {}

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.urlconf_name, self.regex.pattern)

    def _get_reverse_dict(self):
        if not self._reverse_dict and hasattr(self.urlconf_module, 'urlpatterns'):
            for pattern in reversed(self.urlconf_module.urlpatterns):
                if isinstance(pattern, RegexURLResolver):
                    for key, value in pattern.reverse_dict.iteritems():
                        self._reverse_dict[key] = (pattern,) + value
                else:
                    self._reverse_dict[pattern.callback] = (pattern,)
                    self._reverse_dict[pattern.name] = (pattern,)
        return self._reverse_dict
    reverse_dict = property(_get_reverse_dict)

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
                        sub_match_dict = dict([(smart_str(k), v) for k, v in match.groupdict().items()])
                        sub_match_dict.update(self.default_kwargs)
                        for k, v in sub_match[2].iteritems():
                            sub_match_dict[smart_str(k)] = v
                        return sub_match[0], sub_match[1], sub_match_dict
                    tried.append(pattern.regex.pattern)
            raise Resolver404, {'tried': tried, 'path': new_path}

    def _get_urlconf_module(self):
        try:
            return self._urlconf_module
        except AttributeError:
            try:
                self._urlconf_module = __import__(self.urlconf_name, {}, {}, [''])
            except Exception, e:
                # Either an invalid urlconf_name, such as "foo.bar.", or some
                # kind of problem during the actual import.
                raise ImproperlyConfigured, "Error while importing URLconf %r: %s" % (self.urlconf_name, e)
            return self._urlconf_module
    urlconf_module = property(_get_urlconf_module)

    def _get_url_patterns(self):
        return self.urlconf_module.urlpatterns
    url_patterns = property(_get_url_patterns)

    def _resolve_special(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type)
        mod_name, func_name = get_mod_func(callback)
        try:
            return getattr(__import__(mod_name, {}, {}, ['']), func_name), {}
        except (ImportError, AttributeError), e:
            raise ViewDoesNotExist, "Tried %s. Error was: %s" % (callback, str(e))

    def resolve404(self):
        return self._resolve_special('404')

    def resolve500(self):
        return self._resolve_special('500')

    def reverse(self, lookup_view, *args, **kwargs):
        try:
            lookup_view = get_callable(lookup_view, True)
        except (ImportError, AttributeError):
            raise NoReverseMatch
        if lookup_view in self.reverse_dict:
            return u''.join([reverse_helper(part.regex, *args, **kwargs) for part in self.reverse_dict[lookup_view]])
        raise NoReverseMatch

    def reverse_helper(self, lookup_view, *args, **kwargs):
        sub_match = self.reverse(lookup_view, *args, **kwargs)
        result = reverse_helper(self.regex, *args, **kwargs)
        return result + sub_match

def resolve(path, urlconf=None):
    return get_resolver(urlconf).resolve(path)

def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=u'/'):
    args = args or []
    kwargs = kwargs or {}
    return iri_to_uri(prefix +
            get_resolver(urlconf).reverse(viewname, *args, **kwargs))

def clear_url_caches():
    global _resolver_cache
    global _callable_cache
    _resolver_cache.clear()
    _callable_cache.clear()
