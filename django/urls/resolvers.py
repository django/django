"""
This module converts requested URLs to callback view functions.

RegexURLResolver is the main class here. Its resolve() method takes a URL (as
a string) and returns a ResolverMatch object which provides access to all
attributes of the resolved URL match.
"""
from __future__ import unicode_literals

import functools
import re
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache, six
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str, force_text
from django.utils.functional import cached_property
from django.utils.http import RFC3986_SUBDELIMS, urlquote
from django.utils.regex_helper import normalize
from django.utils.translation import get_language

from .exceptions import NoReverseMatch, Resolver404
from .utils import get_callable


class ResolverMatch(object):
    def __init__(self, func, args, kwargs, url_name=None, app_names=None, namespaces=None):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.url_name = url_name

        # If a URLRegexResolver doesn't have a namespace or app_name, it passes
        # in an empty value.
        self.app_names = [x for x in app_names if x] if app_names else []
        self.app_name = ':'.join(self.app_names)
        self.namespaces = [x for x in namespaces if x] if namespaces else []
        self.namespace = ':'.join(self.namespaces)

        if not hasattr(func, '__name__'):
            # A class-based view
            self._func_path = '.'.join([func.__class__.__module__, func.__class__.__name__])
        else:
            # A function-based view
            self._func_path = '.'.join([func.__module__, func.__name__])

        view_path = url_name or self._func_path
        self.view_name = ':'.join(self.namespaces + [view_path])

    def __getitem__(self, index):
        return (self.func, self.args, self.kwargs)[index]

    def __repr__(self):
        return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, app_names=%s, namespaces=%s)" % (
            self._func_path, self.args, self.kwargs, self.url_name,
            self.app_names, self.namespaces,
        )


@lru_cache.lru_cache(maxsize=None)
def get_resolver(urlconf=None):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return RegexURLResolver(r'^/', urlconf)


@lru_cache.lru_cache(maxsize=None)
def get_ns_resolver(ns_pattern, resolver):
    # Build a namespaced resolver for the given parent URLconf pattern.
    # This makes it possible to have captured parameters in the parent
    # URLconf pattern.
    ns_resolver = RegexURLResolver(ns_pattern, resolver.url_patterns)
    return RegexURLResolver(r'^/', [ns_resolver])


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
        Return a compiled regular expression based on the activate language.
        """
        language_code = get_language()
        if language_code not in self._regex_dict:
            regex = self._regex if isinstance(self._regex, six.string_types) else force_text(self._regex)
            try:
                compiled_regex = re.compile(regex, re.UNICODE)
            except re.error as e:
                raise ImproperlyConfigured(
                    '"%s" is not a valid regular expression: %s' %
                    (regex, six.text_type(e))
                )
            self._regex_dict[language_code] = compiled_regex
        return self._regex_dict[language_code]


class RegexURLPattern(LocaleRegexProvider):
    def __init__(self, regex, callback, default_args=None, name=None):
        LocaleRegexProvider.__init__(self, regex)
        self.callback = callback  # the view
        self.default_args = default_args or {}
        self.name = name

    def __repr__(self):
        return force_str('<%s %s %s>' % (self.__class__.__name__, self.name, self.regex.pattern))

    def resolve(self, path):
        match = self.regex.search(path)
        if match:
            # If there are any named groups, use those as kwargs, ignoring
            # non-named groups. Otherwise, pass all non-named arguments as
            # positional arguments.
            kwargs = match.groupdict()
            args = () if kwargs else match.groups()
            # In both cases, pass any extra_kwargs as **kwargs.
            kwargs.update(self.default_args)
            return ResolverMatch(self.callback, args, kwargs, self.name)

    @cached_property
    def lookup_str(self):
        """
        A string that identifies the view (e.g. 'path.to.view_function' or
        'path.to.ClassBasedView').
        """
        callback = self.callback
        # Python 3.5 collapses nested partials, so can change "while" to "if"
        # when it's the minimum supported version.
        while isinstance(callback, functools.partial):
            callback = callback.func
        if not hasattr(callback, '__name__'):
            return callback.__module__ + "." + callback.__class__.__name__
        else:
            return callback.__module__ + "." + callback.__name__


class RegexURLResolver(LocaleRegexProvider):
    def __init__(self, regex, urlconf_name, default_kwargs=None, app_name=None, namespace=None):
        LocaleRegexProvider.__init__(self, regex)
        # urlconf_name is the dotted Python path to the module defining
        # urlpatterns. It may also be an object with an urlpatterns attribute
        # or urlpatterns itself.
        self.urlconf_name = urlconf_name
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
            self.namespace, self.regex.pattern,
        )

    def _populate(self):
        lookups = MultiValueDict()
        namespaces = {}
        apps = {}
        language_code = get_language()
        for pattern in reversed(self.url_patterns):
            if isinstance(pattern, RegexURLPattern):
                self._callback_strs.add(pattern.lookup_str)
            p_pattern = pattern.regex.pattern
            if p_pattern.startswith('^'):
                p_pattern = p_pattern[1:]
            if isinstance(pattern, RegexURLResolver):
                if pattern.namespace:
                    namespaces[pattern.namespace] = (p_pattern, pattern)
                    if pattern.app_name:
                        apps.setdefault(pattern.app_name, []).append(pattern.namespace)
                else:
                    parent_pat = pattern.regex.pattern
                    for name in pattern.reverse_dict:
                        for matches, pat, defaults in pattern.reverse_dict.getlist(name):
                            new_matches = normalize(parent_pat + pat)
                            lookups.appendlist(
                                name,
                                (
                                    new_matches,
                                    p_pattern + pat,
                                    dict(defaults, **pattern.default_kwargs),
                                )
                            )
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

    def _is_callback(self, name):
        if not self._populated:
            self._populate()
        return name in self._callback_strs

    def resolve(self, path):
        path = force_text(path)  # path may be a reverse_lazy object
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
                        tried.extend([pattern] + t for t in sub_tried)
                    else:
                        tried.append([pattern])
                else:
                    if sub_match:
                        # Merge captured arguments in match with submatch
                        sub_match_dict = dict(match.groupdict(), **self.default_kwargs)
                        sub_match_dict.update(sub_match.kwargs)

                        # If there are *any* named groups, ignore all non-named groups.
                        # Otherwise, pass all non-named arguments as positional arguments.
                        sub_match_args = sub_match.args
                        if not sub_match_dict:
                            sub_match_args = match.groups() + sub_match.args

                        return ResolverMatch(
                            sub_match.func,
                            sub_match_args,
                            sub_match_dict,
                            sub_match.url_name,
                            [self.app_name] + sub_match.app_names,
                            [self.namespace] + sub_match.namespaces,
                        )
                    tried.append([pattern])
            raise Resolver404({'tried': tried, 'path': new_path})
        raise Resolver404({'path': path})

    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf_name, six.string_types):
            return import_module(self.urlconf_name)
        else:
            return self.urlconf_name

    @cached_property
    def url_patterns(self):
        # urlconf_module might be a valid set of patterns, so we default to it
        patterns = getattr(self.urlconf_module, "urlpatterns", self.urlconf_module)
        try:
            iter(patterns)
        except TypeError:
            msg = (
                "The included URLconf '{name}' does not appear to have any "
                "patterns in it. If you see valid patterns in the file then "
                "the issue is probably caused by a circular import."
            )
            raise ImproperlyConfigured(msg.format(name=self.urlconf_name))
        return patterns

    def resolve_error_handler(self, view_type):
        callback = getattr(self.urlconf_module, 'handler%s' % view_type, None)
        if not callback:
            # No handler specified in file; use lazy import, since
            # django.conf.urls imports this file.
            from django.conf import urls
            callback = getattr(urls, 'handler%s' % view_type)
        return get_callable(callback), {}

    def _reverse_with_prefix(self, lookup_view, _prefix, *args, **kwargs):
        if args and kwargs:
            raise ValueError("Don't mix *args and **kwargs in call to reverse()!")
        text_args = [force_text(v) for v in args]
        text_kwargs = {k: force_text(v) for (k, v) in kwargs.items()}

        if not self._populated:
            self._populate()

        possibilities = self.reverse_dict.getlist(lookup_view)

        for possibility, pattern, defaults in possibilities:
            for result, params in possibility:
                if args:
                    if len(args) != len(params):
                        continue
                    candidate_subs = dict(zip(params, text_args))
                else:
                    if (set(kwargs.keys()) | set(defaults.keys()) != set(params) |
                            set(defaults.keys())):
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
                candidate_pat = _prefix.replace('%', '%%') + result
                if re.search('^%s%s' % (re.escape(_prefix), pattern), candidate_pat % candidate_subs, re.UNICODE):
                    # safe characters from `pchar` definition of RFC 3986
                    url = urlquote(candidate_pat % candidate_subs, safe=RFC3986_SUBDELIMS + str('/~:@'))
                    # Don't allow construction of scheme relative urls.
                    if url.startswith('//'):
                        url = '/%%2F%s' % url[2:]
                    return url
        # lookup_view can be URL name or callable, but callables are not
        # friendly in error messages.
        m = getattr(lookup_view, '__module__', None)
        n = getattr(lookup_view, '__name__', None)
        if m is not None and n is not None:
            lookup_view_s = "%s.%s" % (m, n)
        else:
            lookup_view_s = lookup_view

        patterns = [pattern for (possibility, pattern, defaults) in possibilities]
        raise NoReverseMatch(
            "Reverse for '%s' with arguments '%s' and keyword "
            "arguments '%s' not found. %d pattern(s) tried: %s" %
            (lookup_view_s, args, kwargs, len(patterns), patterns)
        )


class LocaleRegexURLResolver(RegexURLResolver):
    """
    A URL resolver that always matches the active language code as URL prefix.

    Rather than taking a regex argument, we just override the ``regex``
    function to always return the active language-code as regex.
    """
    def __init__(
        self, urlconf_name, default_kwargs=None, app_name=None, namespace=None,
        prefix_default_language=True,
    ):
        super(LocaleRegexURLResolver, self).__init__(
            None, urlconf_name, default_kwargs, app_name, namespace,
        )
        self.prefix_default_language = prefix_default_language

    @property
    def regex(self):
        language_code = get_language() or settings.LANGUAGE_CODE
        if language_code not in self._regex_dict:
            if language_code == settings.LANGUAGE_CODE and not self.prefix_default_language:
                regex_string = ''
            else:
                regex_string = '^%s/' % language_code
            self._regex_dict[language_code] = re.compile(regex_string, re.UNICODE)
        return self._regex_dict[language_code]
