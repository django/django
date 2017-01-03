from __future__ import unicode_literals

from threading import local

from django.utils import six
from django.utils.encoding import force_text, iri_to_uri
from django.utils.functional import lazy
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit
from django.utils.translation import override

from .exceptions import NoReverseMatch, Resolver404
from .resolvers import get_ns_resolver, get_resolver
from .utils import get_callable

# SCRIPT_NAME prefixes for each thread are stored here. If there's no entry for
# the current thread (which is the only one we ever access), it is assumed to
# be empty.
_prefixes = local()

# Overridden URLconfs for each thread are stored here.
_urlconfs = local()


def resolve(path, urlconf=None):
    if urlconf is None:
        urlconf = get_urlconf()
    return get_resolver(urlconf).resolve(path)


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    if urlconf is None:
        urlconf = get_urlconf()
    resolver = get_resolver(urlconf)
    args = args or []
    kwargs = kwargs or {}

    prefix = get_script_prefix()

    if not isinstance(viewname, six.string_types):
        view = viewname
    else:
        parts = viewname.split(':')
        parts.reverse()
        view = parts[0]
        path = parts[1:]

        if current_app:
            current_path = current_app.split(':')
            current_path.reverse()
        else:
            current_path = None

        resolved_path = []
        ns_pattern = ''
        while path:
            ns = path.pop()
            current_ns = current_path.pop() if current_path else None
            # Lookup the name to see if it could be an app identifier.
            try:
                app_list = resolver.app_dict[ns]
                # Yes! Path part matches an app in the current Resolver.
                if current_ns and current_ns in app_list:
                    # If we are reversing for a particular app, use that
                    # namespace.
                    ns = current_ns
                elif ns not in app_list:
                    # The name isn't shared by one of the instances (i.e.,
                    # the default) so pick the first instance as the default.
                    ns = app_list[0]
            except KeyError:
                pass

            if ns != current_ns:
                current_path = None

            try:
                extra, resolver = resolver.namespace_dict[ns]
                resolved_path.append(ns)
                ns_pattern = ns_pattern + extra
            except KeyError as key:
                if resolved_path:
                    raise NoReverseMatch(
                        "%s is not a registered namespace inside '%s'" %
                        (key, ':'.join(resolved_path))
                    )
                else:
                    raise NoReverseMatch("%s is not a registered namespace" % key)
        if ns_pattern:
            resolver = get_ns_resolver(ns_pattern, resolver)

    return force_text(iri_to_uri(resolver._reverse_with_prefix(view, prefix, *args, **kwargs)))


reverse_lazy = lazy(reverse, six.text_type)


def clear_url_caches():
    get_callable.cache_clear()
    get_resolver.cache_clear()
    get_ns_resolver.cache_clear()


def set_script_prefix(prefix):
    """
    Set the script prefix for the current thread.
    """
    if not prefix.endswith('/'):
        prefix += '/'
    _prefixes.value = prefix


def get_script_prefix():
    """
    Return the currently active script prefix. Useful for client code that
    wishes to construct their own URLs manually (although accessing the request
    instance is normally going to be a lot cleaner).
    """
    return getattr(_prefixes, "value", '/')


def clear_script_prefix():
    """
    Unset the script prefix for the current thread.
    """
    try:
        del _prefixes.value
    except AttributeError:
        pass


def set_urlconf(urlconf_name):
    """
    Set the URLconf for the current thread (overriding the default one in
    settings). If urlconf_name is None, revert back to the default.
    """
    if urlconf_name:
        _urlconfs.value = urlconf_name
    else:
        if hasattr(_urlconfs, "value"):
            del _urlconfs.value


def get_urlconf(default=None):
    """
    Return the root URLconf to use for the current thread if it has been
    changed from the default one.
    """
    return getattr(_urlconfs, "value", default)


def is_valid_path(path, urlconf=None):
    """
    Return True if the given path resolves against the default URL resolver,
    False otherwise. This is a convenience method to make working with "is
    this a match?" cases easier, avoiding try...except blocks.
    """
    try:
        resolve(path, urlconf)
        return True
    except Resolver404:
        return False


def translate_url(url, lang_code):
    """
    Given a URL (absolute or relative), try to get its translated version in
    the `lang_code` language (either by i18n_patterns or by translated regex).
    Return the original URL if no translated version is found.
    """
    parsed = urlsplit(url)
    try:
        match = resolve(parsed.path)
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
