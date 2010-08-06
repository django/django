"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a tuple in this format:

    (view_function, function_args, function_kwargs)
"""

import re

from django.http import Http404
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ViewDoesNotExist
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import iri_to_uri, force_unicode, smart_str
from django.utils.functional import memoize
from django.utils.importlib import import_module
from django.utils.regex_helper import normalize
from django.utils.thread_support import currentThread

_resolver_cache = {} # Maps URLconf modules to RegexURLResolver instances.
_callable_cache = {} # Maps view and url pattern names to their view functions.

# SCRIPT_NAME prefixes for each thread are stored here. If there's no entry for
# the current thread (which is the only one we ever access), it is assumed to
# be empty.
_prefixes = {}

# Overridden URLconfs for each thread are stored here.
_urlconfs = {}

class ResolverMatch(object):
    def __init__(self, func, args, kwargs, url_name=None, app_name=None, namespaces=None):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.app_name = app_name
        if namespaces:
            self.namespaces = [x for x in namespaces if x]
        else:
            self.namespaces = []
        if not url_name:
            if not hasattr(func, '__name__'):
                # An instance of a callable class
                url_name = '.'.join([func.__class__.__module__, func.__class__.__name__])
            else:
                # A function
                url_name = '.'.join([func.__module__, func.__name__])
        self.url_name = url_name

    def namespace(self):
        return ':'.join(self.namespaces)
    namespace = property(namespace)

    def view_name(self):
        return ':'.join([ x for x in [ self.namespace, self.url_name ]  if x ])
    view_name = property(view_name)

    def __getitem__(self, index):
        return (self.func, self.args, self.kwargs)[index]

    def __repr__(self):
        return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name='%s', app_name='%s', namespace='%s')" % (
            self.func, self.args, self.kwargs, self.url_name, self.app_name, self.namespace)

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
                lookup_view = getattr(import_module(mod_name), func_name)
                if not callable(lookup_view):
                    raise AttributeError("'%s.%s' is not a callable." % (mod_name, func_name))
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

            return ResolverMatch(self.callback, args, kwargs, self.name)

    def _get_callback(self):
        if self._callback is not None:
            return self._callback
        try:
            self._callback = get_callable(self._callback_str)
        except ImportError, e:
            mod_name, _ = get_mod_func(self._callback_str)
            raise ViewDoesNotExist("Could not import %s. Error was: %s" % (mod_name, str(e)))
        except AttributeError, e:
            mod_name, func_name = get_mod_func(self._callback_str)
            raise ViewDoesNotExist("Tried %s in module %s. Error was: %s" % (func_name, mod_name, str(e)))
        return self._callback
    callback = property(_get_callback)

class RegexURLResolver(object):
    def __init__(self, regex, urlconf_name, default_kwargs=None, app_name=None, namespace=None):
        # regex is a string representing a regular expression.
        # urlconf_name is a string representing the module containing URLconfs.
        self.regex = re.compile(regex, re.UNICODE)
        self.urlconf_name = urlconf_name
        if not isinstance(urlconf_name, basestring):
            self._urlconf_module = self.urlconf_name
        self.callback = None
        self.default_kwargs = default_kwargs or {}
        self.namespace = namespace
        self.app_name = app_name
        self._reverse_dict = None
        self._namespace_dict = None
        self._app_dict = None

    def __repr__(self):
        return '<%s %s (%s:%s) %s>' % (self.__class__.__name__, self.urlconf_name, self.app_name, self.namespace, self.regex.pattern)

    def _populate(self):
        lookups = MultiValueDict()
        namespaces = {}
        apps = {}
        for pattern in reversed(self.url_patterns):
            p_pattern = pattern.regex.pattern
            if p_pattern.startswith('^'):
                p_pattern = p_pattern[1:]
            if isinstance(pattern, RegexURLResolver):
                if pattern.namespace:
                    namespaces[pattern.namespace] = (p_pattern, pattern)
                    if pattern.app_name:
                        apps.setdefault(pattern.app_name, []).append(pattern.namespace)
                else:
                    parent = normalize(pattern.regex.pattern)
                    for name in pattern.reverse_dict:
                        for matches, pat in pattern.reverse_dict.getlist(name):
                            new_matches = []
                            for piece, p_args in parent:
                                new_matches.extend([(piece + suffix, p_args + args) for (suffix, args) in matches])
                            lookups.appendlist(name, (new_matches, p_pattern + pat))
                    for namespace, (prefix, sub_pattern) in pattern.namespace_dict.items():
                        namespaces[namespace] = (p_pattern + prefix, sub_pattern)
                    for app_name, namespace_list in pattern.app_dict.items():
                        apps.setdefault(app_name, []).extend(namespace_list)
            else:
                bits = normalize(p_pattern)
                lookups.appendlist(pattern.callback, (bits, p_pattern))
                if pattern.name is not None:
                    lookups.appendlist(pattern.name, (bits, p_pattern))
        self._reverse_dict = lookups
        self._namespace_dict = namespaces
        self._app_dict = apps

    def _get_reverse_dict(self):
        if self._reverse_dict is None:
            self._populate()
        return self._reverse_dict
    reverse_dict = property(_get_reverse_dict)

    def _get_namespace_dict(self):
        if self._namespace_dict is None:
            self._populate()
        return self._namespace_dict
    namespace_dict = property(_get_namespace_dict)

    def _get_app_dict(self):
        if self._app_dict is None:
            self._populate()
        return self._app_dict
    app_dict = property(_get_app_dict)

    def resolve(self, path):
        tried = []
        match = self.regex.search(path)
        if match:
            new_path = path[match.end():]
            for pattern in self.url_patterns:
                try:
                    sub_match = pattern.resolve(new_path)
                except Resolver404, e:
                    sub_tried = e.args[0].get('tried')
                    if sub_tried is not None:
                        tried.extend([(pattern.regex.pattern + '   ' + t) for t in sub_tried])
                    else:
                        tried.append(pattern.regex.pattern)
                else:
                    if sub_match:
                        sub_match_dict = dict([(smart_str(k), v) for k, v in match.groupdict().items()])
                        sub_match_dict.update(self.default_kwargs)
                        for k, v in sub_match.kwargs.iteritems():
                            sub_match_dict[smart_str(k)] = v
                        return ResolverMatch(sub_match.func, sub_match.args, sub_match_dict, sub_match.url_name, self.app_name or sub_match.app_name, [self.namespace] + sub_match.namespaces)
                    tried.append(pattern.regex.pattern)
            raise Resolver404({'tried': tried, 'path': new_path})
        raise Resolver404({'path' : path})

    def _get_urlconf_module(self):
        try:
            return self._urlconf_module
        except AttributeError:
            self._urlconf_module = import_module(self.urlconf_name)
            return self._urlconf_module
    urlconf_module = property(_get_urlconf_module)

    def _get_url_patterns(self):
        patterns = getattr(self.urlconf_module, "urlpatterns", self.urlconf_module)
        try:
            iter(patterns)
        except TypeError:
            raise ImproperlyConfigured("The included urlconf %s doesn't have any patterns in it" % self.urlconf_name)
        return patterns
    url_patterns = property(_get_url_patterns)

    def _resolve_special(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type)
        try:
            return get_callable(callback), {}
        except (ImportError, AttributeError), e:
            raise ViewDoesNotExist("Tried %s. Error was: %s" % (callback, str(e)))

    def resolve404(self):
        return self._resolve_special('404')

    def resolve500(self):
        return self._resolve_special('500')

    def reverse(self, lookup_view, *args, **kwargs):
        if args and kwargs:
            raise ValueError("Don't mix *args and **kwargs in call to reverse()!")
        try:
            lookup_view = get_callable(lookup_view, True)
        except (ImportError, AttributeError), e:
            raise NoReverseMatch("Error importing '%s': %s." % (lookup_view, e))
        possibilities = self.reverse_dict.getlist(lookup_view)
        for possibility, pattern in possibilities:
            for result, params in possibility:
                if args:
                    if len(args) != len(params):
                        continue
                    unicode_args = [force_unicode(val) for val in args]
                    candidate =  result % dict(zip(params, unicode_args))
                else:
                    if set(kwargs.keys()) != set(params):
                        continue
                    unicode_kwargs = dict([(k, force_unicode(v)) for (k, v) in kwargs.items()])
                    candidate = result % unicode_kwargs
                if re.search(u'^%s' % pattern, candidate, re.UNICODE):
                    return candidate
        # lookup_view can be URL label, or dotted path, or callable, Any of
        # these can be passed in at the top, but callables are not friendly in
        # error messages.
        m = getattr(lookup_view, '__module__', None)
        n = getattr(lookup_view, '__name__', None)
        if m is not None and n is not None:
            lookup_view_s = "%s.%s" % (m, n)
        else:
            lookup_view_s = lookup_view
        raise NoReverseMatch("Reverse for '%s' with arguments '%s' and keyword "
                "arguments '%s' not found." % (lookup_view_s, args, kwargs))

def resolve(path, urlconf=None):
    if urlconf is None:
        urlconf = get_urlconf()
    return get_resolver(urlconf).resolve(path)

def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    if urlconf is None:
        urlconf = get_urlconf()
    resolver = get_resolver(urlconf)
    args = args or []
    kwargs = kwargs or {}

    if prefix is None:
        prefix = get_script_prefix()

    if not isinstance(viewname, basestring):
        view = viewname
    else:
        parts = viewname.split(':')
        parts.reverse()
        view = parts[0]
        path = parts[1:]

        resolved_path = []
        while path:
            ns = path.pop()

            # Lookup the name to see if it could be an app identifier
            try:
                app_list = resolver.app_dict[ns]
                # Yes! Path part matches an app in the current Resolver
                if current_app and current_app in app_list:
                    # If we are reversing for a particular app, use that namespace
                    ns = current_app
                elif ns not in app_list:
                    # The name isn't shared by one of the instances (i.e., the default)
                    # so just pick the first instance as the default.
                    ns = app_list[0]
            except KeyError:
                pass

            try:
                extra, resolver = resolver.namespace_dict[ns]
                resolved_path.append(ns)
                prefix = prefix + extra
            except KeyError, key:
                if resolved_path:
                    raise NoReverseMatch("%s is not a registered namespace inside '%s'" % (key, ':'.join(resolved_path)))
                else:
                    raise NoReverseMatch("%s is not a registered namespace" % key)

    return iri_to_uri(u'%s%s' % (prefix, resolver.reverse(view,
            *args, **kwargs)))

def clear_url_caches():
    global _resolver_cache
    global _callable_cache
    _resolver_cache.clear()
    _callable_cache.clear()

def set_script_prefix(prefix):
    """
    Sets the script prefix for the current thread.
    """
    if not prefix.endswith('/'):
        prefix += '/'
    _prefixes[currentThread()] = prefix

def get_script_prefix():
    """
    Returns the currently active script prefix. Useful for client code that
    wishes to construct their own URLs manually (although accessing the request
    instance is normally going to be a lot cleaner).
    """
    return _prefixes.get(currentThread(), u'/')

def set_urlconf(urlconf_name):
    """
    Sets the URLconf for the current thread (overriding the default one in
    settings). Set to None to revert back to the default.
    """
    thread = currentThread()
    if urlconf_name:
        _urlconfs[thread] = urlconf_name
    else:
        # faster than wrapping in a try/except
        if thread in _urlconfs:
            del _urlconfs[thread]

def get_urlconf(default=None):
    """
    Returns the root URLconf to use for the current thread if it has been
    changed from the default one.
    """
    thread = currentThread()
    if thread in _urlconfs:
        return _urlconfs[thread]
    return default
