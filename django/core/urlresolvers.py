"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a tuple in this format:

    (view_function, function_args, function_kwargs)
"""
from __future__ import unicode_literals

import functools
import re
from threading import local

from django.http import Http404
from django.core.exceptions import ImproperlyConfigured, ViewDoesNotExist
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str, force_text, iri_to_uri
from django.utils.functional import memoize, lazy
from django.utils.http import urlquote
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule
from django.utils.regex_helper import normalize
from django.utils import six
from django.utils.translation import get_language


_resolver_cache = {} # Maps URLconf modules to RegexURLResolver instances.
_ns_resolver_cache = {} # Maps namespaces to RegexURLResolver instances.
_callable_cache = {} # Maps view and url pattern names to their view functions.

# SCRIPT_NAME prefixes for each thread are stored here. If there's no entry for
# the current thread (which is the only one we ever access), it is assumed to
# be empty.
_prefixes = local()

# Overridden URLconfs for each thread are stored here.
_urlconfs = local()


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

    @property
    def namespace(self):
        return ':'.join(self.namespaces)

    @property
    def view_name(self):
        return ':'.join([ x for x in [ self.namespace, self.url_name ]  if x ])

    def __getitem__(self, index):
        return (self.func, self.args, self.kwargs)[index]

    def __repr__(self):
        return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name='%s', app_name='%s', namespace='%s')" % (
            self.func, self.args, self.kwargs, self.url_name, self.app_name, self.namespace)

class Resolver404(Http404):
    pass

class NoReverseMatch(Exception):
    pass

def get_callable(lookup_view, can_fail=False):
    """
    Convert a string version of a function name to the callable object.

    If the lookup_view is not an import path, it is assumed to be a URL pattern
    label and the original string is returned.

    If can_fail is True, lookup_view might be a URL pattern label, so errors
    during the import fail and the string is returned.
    """
    if not callable(lookup_view):
        mod_name, func_name = get_mod_func(lookup_view)
        if func_name == '':
            return lookup_view

        try:
            mod = import_module(mod_name)
        except ImportError:
            parentmod, submod = get_mod_func(mod_name)
            if (not can_fail and submod != '' and
                    not module_has_submodule(import_module(parentmod), submod)):
                raise ViewDoesNotExist(
                    "Could not import %s. Parent module %s does not exist." %
                    (lookup_view, mod_name))
            if not can_fail:
                raise
        else:
            try:
                lookup_view = getattr(mod, func_name)
                if not callable(lookup_view):
                    raise ViewDoesNotExist(
                        "Could not import %s.%s. View is not callable." %
                        (mod_name, func_name))
            except AttributeError:
                if not can_fail:
                    raise ViewDoesNotExist(
                        "Could not import %s. View does not exist in module %s." %
                        (lookup_view, mod_name))
    return lookup_view
get_callable = memoize(get_callable, _callable_cache, 1)

def get_resolver(urlconf):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return RegexURLResolver(r'^/', urlconf)
get_resolver = memoize(get_resolver, _resolver_cache, 1)

def get_ns_resolver(ns_pattern, resolver):
    # Build a namespaced resolver for the given parent urlconf pattern.
    # This makes it possible to have captured parameters in the parent
    # urlconf pattern.
    ns_resolver = RegexURLResolver(ns_pattern,
                                          resolver.url_patterns)
    return RegexURLResolver(r'^/', [ns_resolver])
get_ns_resolver = memoize(get_ns_resolver, _ns_resolver_cache, 2)

def get_mod_func(callback):
    # Converts 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot+1:]

class LocaleRegexProvider(object):
    """
    A mixin to provide a default regex property which can vary by active
    language.

    """
    def __init__(self, regex):
        # regex is either a string representing a regular expression, or a
        # translatable string (using ugettext_lazy) representing a regular
        # expression.
        self._regex = regex
        self._regex_dict = {}


    @property
    def regex(self):
        """
        Returns a compiled regular expression, depending upon the activated
        language-code.
        """
        language_code = get_language()
        if language_code not in self._regex_dict:
            if isinstance(self._regex, six.string_types):
                regex = self._regex
            else:
                regex = force_text(self._regex)
            try:
                compiled_regex = re.compile(regex, re.UNICODE)
            except re.error as e:
                raise ImproperlyConfigured(
                    '"%s" is not a valid regular expression: %s' %
                    (regex, six.text_type(e)))

            self._regex_dict[language_code] = compiled_regex
        return self._regex_dict[language_code]


class RegexURLPattern(LocaleRegexProvider):
    def __init__(self, regex, callback, default_args=None, name=None):
        LocaleRegexProvider.__init__(self, regex)
        # callback is either a string like 'foo.views.news.stories.story_detail'
        # which represents the path to a module and a view function name, or a
        # callable object (view).
        if callable(callback):
            self._callback = callback
        else:
            self._callback = None
            self._callback_str = callback
        self.default_args = default_args or {}
        self.name = name

    def __repr__(self):
        return force_str('<%s %s %s>' % (self.__class__.__name__, self.name, self.regex.pattern))

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

    @property
    def callback(self):
        if self._callback is not None:
            return self._callback

        self._callback = get_callable(self._callback_str)
        return self._callback

class RegexURLResolver(LocaleRegexProvider):
    def __init__(self, regex, urlconf_name, default_kwargs=None, app_name=None, namespace=None):
        LocaleRegexProvider.__init__(self, regex)
        # urlconf_name is a string representing the module containing URLconfs.
        self.urlconf_name = urlconf_name
        if not isinstance(urlconf_name, six.string_types):
            self._urlconf_module = self.urlconf_name
        self.callback = None
        self.default_kwargs = default_kwargs or {}
        self.namespace = namespace
        self.app_name = app_name
        self._reverse_dict = {}
        self._namespace_dict = {}
        self._app_dict = {}
        # set of dotted paths to all functions and classes that are used in
        # urlpatterns
        self._callback_strs = set()
        self._populated = False

    def __repr__(self):
        if isinstance(self.urlconf_name, list) and len(self.urlconf_name):
            # Don't bother to output the whole list, it can be huge
            urlconf_repr = '<%s list>' % self.urlconf_name[0].__class__.__name__
        else:
            urlconf_repr = repr(self.urlconf_name)
        return str('<%s %s (%s:%s) %s>') % (
            self.__class__.__name__, urlconf_repr, self.app_name,
            self.namespace, self.regex.pattern)

    def _populate(self):
        lookups = MultiValueDict()
        namespaces = {}
        apps = {}
        language_code = get_language()
        for pattern in reversed(self.url_patterns):
            if hasattr(pattern, '_callback_str'):
                self._callback_strs.add(pattern._callback_str)
            elif hasattr(pattern, '_callback'):
                callback = pattern._callback
                if isinstance(callback, functools.partial):
                    callback = callback.func

                if not hasattr(callback, '__name__'):
                    lookup_str = callback.__module__ + "." + callback.__class__.__name__
                else:
                    lookup_str = callback.__module__ + "." + callback.__name__
                self._callback_strs.add(lookup_str)
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
                        for matches, pat, defaults in pattern.reverse_dict.getlist(name):
                            new_matches = []
                            for piece, p_args in parent:
                                new_matches.extend([(piece + suffix, p_args + args) for (suffix, args) in matches])
                            lookups.appendlist(name, (new_matches, p_pattern + pat, dict(defaults, **pattern.default_kwargs)))
                    for namespace, (prefix, sub_pattern) in pattern.namespace_dict.items():
                        namespaces[namespace] = (p_pattern + prefix, sub_pattern)
                    for app_name, namespace_list in pattern.app_dict.items():
                        apps.setdefault(app_name, []).extend(namespace_list)
                    self._callback_strs.update(pattern._callback_strs)
            else:
                bits = normalize(p_pattern)
                lookups.appendlist(pattern.callback, (bits, p_pattern, pattern.default_args))
                if pattern.name is not None:
                    lookups.appendlist(pattern.name, (bits, p_pattern, pattern.default_args))
        self._reverse_dict[language_code] = lookups
        self._namespace_dict[language_code] = namespaces
        self._app_dict[language_code] = apps
        self._populated = True

    @property
    def reverse_dict(self):
        language_code = get_language()
        if language_code not in self._reverse_dict:
            self._populate()
        return self._reverse_dict[language_code]

    @property
    def namespace_dict(self):
        language_code = get_language()
        if language_code not in self._namespace_dict:
            self._populate()
        return self._namespace_dict[language_code]

    @property
    def app_dict(self):
        language_code = get_language()
        if language_code not in self._app_dict:
            self._populate()
        return self._app_dict[language_code]

    def resolve(self, path):
        tried = []
        match = self.regex.search(path)
        if match:
            new_path = path[match.end():]
            for pattern in self.url_patterns:
                try:
                    sub_match = pattern.resolve(new_path)
                except Resolver404 as e:
                    sub_tried = e.args[0].get('tried')
                    if sub_tried is not None:
                        tried.extend([[pattern] + t for t in sub_tried])
                    else:
                        tried.append([pattern])
                else:
                    if sub_match:
                        sub_match_dict = dict(match.groupdict(), **self.default_kwargs)
                        sub_match_dict.update(sub_match.kwargs)
                        return ResolverMatch(sub_match.func, sub_match.args, sub_match_dict, sub_match.url_name, self.app_name or sub_match.app_name, [self.namespace] + sub_match.namespaces)
                    tried.append([pattern])
            raise Resolver404({'tried': tried, 'path': new_path})
        raise Resolver404({'path' : path})

    @property
    def urlconf_module(self):
        try:
            return self._urlconf_module
        except AttributeError:
            self._urlconf_module = import_module(self.urlconf_name)
            return self._urlconf_module

    @property
    def url_patterns(self):
        patterns = getattr(self.urlconf_module, "urlpatterns", self.urlconf_module)
        try:
            iter(patterns)
        except TypeError:
            raise ImproperlyConfigured("The included urlconf %s doesn't have any patterns in it" % self.urlconf_name)
        return patterns

    def _resolve_special(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type, None)
        if not callback:
            # No handler specified in file; use default
            # Lazy import, since django.urls imports this file
            from django.conf import urls
            callback = getattr(urls, 'handler%s' % view_type)
        return get_callable(callback), {}

    def resolve400(self):
        return self._resolve_special('400')

    def resolve403(self):
        return self._resolve_special('403')

    def resolve404(self):
        return self._resolve_special('404')

    def resolve500(self):
        return self._resolve_special('500')

    def reverse(self, lookup_view, *args, **kwargs):
        return self._reverse_with_prefix(lookup_view, '', *args, **kwargs)

    def _reverse_with_prefix(self, lookup_view, _prefix, *args, **kwargs):
        if args and kwargs:
            raise ValueError("Don't mix *args and **kwargs in call to reverse()!")
        text_args = [force_text(v) for v in args]
        text_kwargs = dict((k, force_text(v)) for (k, v) in kwargs.items())

        if not self._populated:
            self._populate()

        try:
            if lookup_view in self._callback_strs:
                lookup_view = get_callable(lookup_view, True)
        except (ImportError, AttributeError) as e:
            raise NoReverseMatch("Error importing '%s': %s." % (lookup_view, e))
        possibilities = self.reverse_dict.getlist(lookup_view)

        prefix_norm, prefix_args = normalize(urlquote(_prefix))[0]
        for possibility, pattern, defaults in possibilities:
            for result, params in possibility:
                if args:
                    if len(args) != len(params) + len(prefix_args):
                        continue
                    candidate_subs = dict(zip(prefix_args + params, text_args))
                else:
                    if set(kwargs.keys()) | set(defaults.keys()) != set(params) | set(defaults.keys()) | set(prefix_args):
                        continue
                    matches = True
                    for k, v in defaults.items():
                        if kwargs.get(k, v) != v:
                            matches = False
                            break
                    if not matches:
                        continue
                    candidate_subs = text_kwargs
                # WSGI provides decoded URLs, without %xx escapes, and the URL
                # resolver operates on such URLs. First substitute arguments
                # without quoting to build a decoded URL and look for a match.
                # Then, if we have a match, redo the substitution with quoted
                # arguments in order to return a properly encoded URL.
                candidate_pat = prefix_norm.replace('%', '%%') + result
                if re.search('^%s%s' % (prefix_norm, pattern), candidate_pat % candidate_subs, re.UNICODE):
                    candidate_subs = dict((k, urlquote(v)) for (k, v) in candidate_subs.items())
                    return candidate_pat % candidate_subs
        # lookup_view can be URL label, or dotted path, or callable, Any of
        # these can be passed in at the top, but callables are not friendly in
        # error messages.
        m = getattr(lookup_view, '__module__', None)
        n = getattr(lookup_view, '__name__', None)
        if m is not None and n is not None:
            lookup_view_s = "%s.%s" % (m, n)
        else:
            lookup_view_s = lookup_view

        patterns = [pattern for (possibility, pattern, defaults) in possibilities]
        raise NoReverseMatch("Reverse for '%s' with arguments '%s' and keyword "
                "arguments '%s' not found. %d pattern(s) tried: %s" %
                             (lookup_view_s, args, kwargs, len(patterns), patterns))

class LocaleRegexURLResolver(RegexURLResolver):
    """
    A URL resolver that always matches the active language code as URL prefix.

    Rather than taking a regex argument, we just override the ``regex``
    function to always return the active language-code as regex.
    """
    def __init__(self, urlconf_name, default_kwargs=None, app_name=None, namespace=None):
        super(LocaleRegexURLResolver, self).__init__(
            None, urlconf_name, default_kwargs, app_name, namespace)

    @property
    def regex(self):
        language_code = get_language()
        if language_code not in self._regex_dict:
            regex_compiled = re.compile('^%s/' % language_code, re.UNICODE)
            self._regex_dict[language_code] = regex_compiled
        return self._regex_dict[language_code]

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

    if not isinstance(viewname, six.string_types):
        view = viewname
    else:
        parts = viewname.split(':')
        parts.reverse()
        view = parts[0]
        path = parts[1:]

        resolved_path = []
        ns_pattern = ''
        while path:
            ns = path.pop()

            # Lookup the name to see if it could be an app identifier
            try:
                app_list = resolver.app_dict[ns]
                # Yes! Path part matches an app in the current Resolver
                if current_app and current_app in app_list:
                    # If we are reversing for a particular app,
                    # use that namespace
                    ns = current_app
                elif ns not in app_list:
                    # The name isn't shared by one of the instances
                    # (i.e., the default) so just pick the first instance
                    # as the default.
                    ns = app_list[0]
            except KeyError:
                pass

            try:
                extra, resolver = resolver.namespace_dict[ns]
                resolved_path.append(ns)
                ns_pattern = ns_pattern + extra
            except KeyError as key:
                if resolved_path:
                    raise NoReverseMatch(
                        "%s is not a registered namespace inside '%s'" %
                        (key, ':'.join(resolved_path)))
                else:
                    raise NoReverseMatch("%s is not a registered namespace" %
                                         key)
        if ns_pattern:
            resolver = get_ns_resolver(ns_pattern, resolver)

    return iri_to_uri(resolver._reverse_with_prefix(view, prefix, *args, **kwargs))

reverse_lazy = lazy(reverse, str)

def clear_url_caches():
    global _resolver_cache
    global _ns_resolver_cache
    global _callable_cache
    _resolver_cache.clear()
    _ns_resolver_cache.clear()
    _callable_cache.clear()

def set_script_prefix(prefix):
    """
    Sets the script prefix for the current thread.
    """
    if not prefix.endswith('/'):
        prefix += '/'
    _prefixes.value = prefix

def get_script_prefix():
    """
    Returns the currently active script prefix. Useful for client code that
    wishes to construct their own URLs manually (although accessing the request
    instance is normally going to be a lot cleaner).
    """
    return getattr(_prefixes, "value", '/')

def clear_script_prefix():
    """
    Unsets the script prefix for the current thread.
    """
    try:
        del _prefixes.value
    except AttributeError:
        pass

def set_urlconf(urlconf_name):
    """
    Sets the URLconf for the current thread (overriding the default one in
    settings). Set to None to revert back to the default.
    """
    if urlconf_name:
        _urlconfs.value = urlconf_name
    else:
        if hasattr(_urlconfs, "value"):
            del _urlconfs.value

def get_urlconf(default=None):
    """
    Returns the root URLconf to use for the current thread if it has been
    changed from the default one.
    """
    return getattr(_urlconfs, "value", default)

def is_valid_path(path, urlconf=None):
    """
    Returns True if the given path resolves against the default URL resolver,
    False otherwise.

    This is a convenience method to make working with "is this a match?" cases
    easier, avoiding unnecessarily indented try...except blocks.
    """
    try:
        resolve(path, urlconf)
        return True
    except Resolver404:
        return False
