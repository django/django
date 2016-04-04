from __future__ import unicode_literals

import functools
from importlib import import_module

from django.core.exceptions import ViewDoesNotExist
from django.http import QueryDict
from django.utils import lru_cache, six
from django.utils.encoding import iri_to_uri
from django.utils.http import RFC3986_SUBDELIMS, urlquote
from django.utils.module_loading import module_has_submodule
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit


def describe_constraints(constraints):
    url = URL()
    for constraint in constraints:
        url = constraint.describe(url)
    return url.describe()


def get_lookup_string(view):
    """
    A string that identifies the view (e.g. 'path.to.view_function' or
    'path.to.ClassBasedView').
    """
    # Python 3.5 collapses nested partials, so can change "while" to "if"
    # when it's the minimum supported version.
    while isinstance(view, functools.partial):
        view = view.func
    if not hasattr(view, '__name__'):
        return view.__module__ + "." + view.__class__.__name__
    else:
        return view.__module__ + "." + view.__name__


@lru_cache.lru_cache(maxsize=None)
def get_callable(lookup_view):
    """
    Return a callable corresponding to lookup_view.
    * If lookup_view is already a callable, return it.
    * If lookup_view is a string import path that can be resolved to a callable,
      import that callable and return it, otherwise raise an exception
      (ImportError or ViewDoesNotExist).
    """
    if callable(lookup_view):
        return lookup_view

    if not isinstance(lookup_view, six.string_types):
        raise ViewDoesNotExist("'%s' is not a callable or a dot-notation path" % lookup_view)

    mod_name, func_name = get_mod_func(lookup_view)
    if not func_name:  # No '.' in lookup_view
        raise ImportError("Could not import '%s'. The path must be fully qualified." % lookup_view)

    try:
        mod = import_module(mod_name)
    except ImportError:
        parentmod, submod = get_mod_func(mod_name)
        if submod and not module_has_submodule(import_module(parentmod), submod):
            raise ViewDoesNotExist(
                "Could not import '%s'. Parent module %s does not exist." %
                (lookup_view, mod_name)
            )
        else:
            raise
    else:
        try:
            view_func = getattr(mod, func_name)
        except AttributeError:
            raise ViewDoesNotExist(
                "Could not import '%s'. View does not exist in module %s." %
                (lookup_view, mod_name)
            )
        else:
            if not callable(view_func):
                raise ViewDoesNotExist(
                    "Could not import '%s.%s'. View is not callable." %
                    (mod_name, func_name)
                )
            return view_func


def get_mod_func(callback):
    # Convert 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot + 1:]


class URL(object):
    __slots__ = ['scheme', 'host', 'path', 'query', 'fragment', 'params']

    def __init__(self, scheme='', host='', path='', query=None, fragment='', params=None):
        self.scheme = scheme
        self.host = host
        self.path = path
        if isinstance(query, six.string_types):
            self.query = QueryDict(iri_to_uri(query), mutable=True)
        else:
            self.query = query.copy() if query else QueryDict(mutable=True)
        self.fragment = fragment
        self.params = params or {}

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
        return "<URL '%s'>" % str(self)

    def __str__(self):
        path = urlquote(self.path, safe=RFC3986_SUBDELIMS + str('/~:@'))
        if path.startswith('//'):
            path = '/%%2F%s' % path[2:]
        return urlunsplit((
            self.scheme,
            self.host,
            path,
            self.query.urlencode(),
            iri_to_uri(self.fragment) if self.fragment else ''
        ))

    def describe(self):
        description = urlunsplit((self.scheme, self.host, self.path, self.query, self.fragment))
        if self.params:
            description += ' [%s]' % (
                ', '.join('%s=%r' % (k, v) for k, v in self.params.items()),
            )
        return description

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query, self.fragment, self.params,
        )
