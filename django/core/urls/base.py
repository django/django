from __future__ import unicode_literals

import warnings
from threading import local

from django.utils import lru_cache, six
from django.utils.deprecation import RemovedInDjango110Warning
from django.utils.encoding import force_text, iri_to_uri, escape_query_string
from django.utils.functional import lazy
from django.utils.http import RFC3986_SUBDELIMS, urlquote
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit

from .constraints import RegexPattern
from .exceptions import NoReverseMatch
from .resolvers import Resolver


# SCRIPT_NAME prefixes for each thread are stored here. If there's no entry for
# the current thread (which is the only one we ever access), it is assumed to
# be empty.
_prefixes = local()

# Overridden URLconfs for each thread are stored here.
_urlconfs = local()


@lru_cache.lru_cache(maxsize=None)
def get_resolver(urlconf):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    return Resolver(urlconf, constraints=[RegexPattern(r'^/')])


def resolve(path, urlconf=None, request=None):
    path = force_text(path)
    if urlconf is None:
        urlconf = get_urlconf()
    return get_resolver(urlconf).resolve(path, request)


class URL(object):
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
            self.path or '/',
            escape_query_string(self.query_string),
            self.fragment
        )))

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query_string, self.fragment
        )


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None, strings_only=True):
    if urlconf is None:
        urlconf = get_urlconf()

    resolver = get_resolver(urlconf)
    args = args or ()
    text_args = [force_text(x) for x in args]
    kwargs = kwargs or {}
    text_kwargs = {k: force_text(v) for k, v in kwargs.items()}

    prefix = get_script_prefix()[:-1]  # Trailing slash is already there

    original_lookup = viewname
    try:
        if resolver._is_callback(viewname):
            from django.core.urls.utils import get_callable
            viewname = get_callable(viewname, True)
    except (ImportError, AttributeError) as e:
        raise NoReverseMatch("Error importing '%s': %s." % (viewname, e))
    else:
        if not callable(original_lookup) and callable(viewname):
            warnings.warn(
                'Reversing by dotted path is deprecated (%s).' % original_lookup,
                RemovedInDjango110Warning, stacklevel=3
            )

    if isinstance(viewname, six.string_types):
        lookup = viewname.split(':')
    elif viewname:
        lookup = [viewname]
    else:
        raise NoReverseMatch()

    current_app = current_app.split(':') if current_app else []

    lookup = resolver.resolve_namespace(lookup, current_app)

    patterns = []
    for constraints, default_kwargs in resolver.search(lookup):
        url = URL()
        new_args, new_kwargs = text_args, text_kwargs
        try:
            for constraint in constraints:
                url, new_args, new_kwargs = constraint.construct(url, *new_args, **new_kwargs)
            if new_kwargs:
                if any(name not in default_kwargs for name in new_kwargs):
                    raise NoReverseMatch()
                for k, v in default_kwargs.items():
                    if kwargs.get(k, v) != v:
                        raise NoReverseMatch()
            if new_args:
                raise NoReverseMatch()
        except NoReverseMatch:
            # We don't need the leading slash of the root pattern here
            patterns.append(constraints[1:])
        else:
            url.path = urlquote(prefix + force_text(url.path), safe=RFC3986_SUBDELIMS + str('/~:@'))
            if url.path.startswith('//'):
                url.path = '/%%2F%s' % url.path[2:]
            return force_text(url) if strings_only else url

    raise NoReverseMatch(
        "Reverse for '%s' with arguments '%s' and keyword "
        "arguments '%s' not found. %d pattern(s) tried: %s" %
        (viewname, args, kwargs, len(patterns), [str('').join(c.describe() for c in constraints) for constraints in patterns])
    )


reverse_lazy = lazy(reverse, URL, six.text_type)


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
