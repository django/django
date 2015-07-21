from __future__ import unicode_literals

from importlib import import_module

from django.core.exceptions import ViewDoesNotExist
from django.utils import lru_cache, six
from django.utils.encoding import iri_to_uri, escape_query_string
from django.utils.module_loading import module_has_submodule
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit
from django.utils.translation import override


@lru_cache.lru_cache(maxsize=None)
def get_callable(lookup_view, can_fail=False):
    """
    Return a callable corresponding to lookup_view. This function is used
    by both resolve() and reverse(), so can_fail allows the caller to choose
    between returning the input as is and raising an exception when the input
    string can't be interpreted as an import path.

    If lookup_view is already a callable, return it.
    If lookup_view is a string import path that can be resolved to a callable,
      import that callable and return it.
    If lookup_view is some other kind of string and can_fail is True, the string
      is returned as is. If can_fail is False, an exception is raised (either
      ImportError or ViewDoesNotExist).
    """
    if callable(lookup_view):
        return lookup_view

    if not isinstance(lookup_view, six.string_types):
        raise ViewDoesNotExist(
            "'%s' is not a callable or a dot-notation path" % lookup_view
        )

    mod_name, func_name = get_mod_func(lookup_view)
    if not func_name:  # No '.' in lookup_view
        if can_fail:
            return lookup_view
        else:
            raise ImportError(
                "Could not import '%s'. The path must be fully qualified." %
                lookup_view)

    try:
        mod = import_module(mod_name)
    except ImportError:
        if can_fail:
            return lookup_view
        else:
            parentmod, submod = get_mod_func(mod_name)
            if submod and not module_has_submodule(import_module(parentmod), submod):
                raise ViewDoesNotExist(
                    "Could not import '%s'. Parent module %s does not exist." %
                    (lookup_view, mod_name))
            else:
                raise
    else:
        try:
            view_func = getattr(mod, func_name)
        except AttributeError:
            if can_fail:
                return lookup_view
            else:
                raise ViewDoesNotExist(
                    "Could not import '%s'. View does not exist in module %s." %
                    (lookup_view, mod_name))
        else:
            if not callable(view_func):
                # For backwards compatibility this is raised regardless of can_fail
                raise ViewDoesNotExist(
                    "Could not import '%s.%s'. View is not callable." %
                    (mod_name, func_name))

            return view_func


def get_mod_func(callback):
    # Converts 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot + 1:]


class URL(object):
    __slots__ = ['scheme', 'host', 'path', 'query_string', 'fragment']

    def __init__(self, scheme='', host='', path='', query_string='', fragment=''):
        self.scheme = scheme
        self.host = host
        self.path = path
        self.query_string = query_string
        self.fragment = fragment

    @classmethod
    def from_location(cls, location):
        return cls(*urlsplit(location))

    @classmethod
    def from_request(cls, request):
        return cls(
            request.scheme,
            request.get_host(),
            request.path,
            request.META.get('QUERY_STRING', ''),
            ''
        )

    def __repr__(self):
        return "<URL '%s'>" % urlunsplit((self.scheme, self.host, self.path, self.query_string, self.fragment))

    def __str__(self):
        return iri_to_uri(urlunsplit((
            self.scheme,
            self.host,
            self.path,
            escape_query_string(self.query_string),
            self.fragment
        )))

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query_string, self.fragment
        )


def resolve_error_handler(urlconf, view_type):
    callback = getattr(urlconf, 'handler%s' % view_type, None)
    if not callback:
        # No handler specified in file; use default
        # Lazy import, since django.urls imports this file
        from django.conf import urls
        callback = getattr(urls, 'handler%s' % view_type)
    return get_callable(callback), {}


def is_valid_path(path, urlconf=None, request=None):
    """
    Returns True if the given path resolves against the default URL resolver,
    False otherwise.

    This is a convenience method to make working with "is this a match?" cases
    easier, avoiding unnecessarily indented try...except blocks.
    """
    from django.core.urls import Resolver404, resolve
    try:
        resolve(path, urlconf, request)
        return True
    except Resolver404:
        return False


def translate_url(url, lang_code, request=None):
    """
    Given a URL (absolute or relative), try to get its translated version in
    the `lang_code` language (either by i18n_patterns or by translated regex).
    Return the original URL if no translated version is found.
    """
    from django.core.urls import Resolver404, NoReverseMatch, resolve, reverse
    parsed = urlsplit(url)
    try:
        match = resolve(parsed.path, request=request)
    except Resolver404:
        pass
    else:
        to_be_reversed = "%s:%s" % (match.namespace, match.url_name) if match.namespace else match.url_name
        with override(lang_code):
            try:
                url = reverse(to_be_reversed, args=match.args, kwargs=match.kwargs)
            except NoReverseMatch:
                pass
            else:
                url = urlunsplit((parsed.scheme, parsed.netloc, url, parsed.query, parsed.fragment))
    return url


def clear_url_caches():
    from django.core.urls import get_resolver
    get_callable.cache_clear()
    get_resolver.cache_clear()
