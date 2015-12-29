from __future__ import unicode_literals

from threading import local

from django.utils import six
from django.utils.encoding import force_text
from django.utils.functional import lazy

from .dispatcher import get_dispatcher
from .resolvers import get_resolver
from .utils import URL, get_callable

# SCRIPT_NAME prefixes for each thread are stored here. If there's no entry for
# the current thread (which is the only one we ever access), it is assumed to
# be empty.
_prefixes = local()

# Overridden URLconfs for each thread are stored here.
_urlconfs = local()


def resolve(path, urlconf=None, request=None):
    path = force_text(path)
    if urlconf is None:
        urlconf = get_urlconf()
    return get_resolver(urlconf).resolve(path, request)


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    if urlconf is None:
        urlconf = get_urlconf()

    dispatcher = get_dispatcher(urlconf)
    if not dispatcher.ready:
        raise RuntimeError(
            "Can't reverse urls when the url dispatcher hasn't "
            "been loaded. Use reverse_lazy() instead."
        )
    args = args or ()
    kwargs = kwargs or {}

    lookup = dispatcher.resolve_namespace(viewname, current_app)

    return dispatcher.reverse(lookup, *args, **kwargs)


reverse_lazy = lazy(reverse, URL, six.text_type)


def clear_url_caches():
    get_callable.cache_clear()
    get_dispatcher.cache_clear()
    get_resolver.cache_clear()


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


def resolve_error_handler(urlconf, view_type):
    dispatcher = get_dispatcher(urlconf)
    return dispatcher.resolve_error_handler(view_type)


def is_valid_path(path, urlconf=None, request=None):
    """
    Returns True if the given path resolves against the default URL resolver,
    False otherwise.

    This is a convenience method to make working with "is this a match?" cases
    easier, avoiding unnecessarily indented try...except blocks.
    """
    if urlconf is None:
        urlconf = get_urlconf()
    dispatcher = get_dispatcher(urlconf)
    return dispatcher.is_valid_path(path, request)


def translate_url(url, lang_code, request=None):
    """
    Given a URL (absolute or relative), try to get its translated version in
    the `lang_code` language (either by i18n_patterns or by translated regex).
    Return the original URL if no translated version is found.
    """
    urlconf = get_urlconf()
    dispatcher = get_dispatcher(urlconf)
    return dispatcher.translate_url(url, lang_code, request)
