from importlib import import_module
import warnings

from freedom.core.urlresolvers import (RegexURLPattern,
    RegexURLResolver, LocaleRegexURLResolver)
from freedom.core.exceptions import ImproperlyConfigured
from freedom.utils import six
from freedom.utils.deprecation import RemovedInFreedom20Warning


__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include', 'patterns', 'url']

handler400 = 'freedom.views.defaults.bad_request'
handler403 = 'freedom.views.defaults.permission_denied'
handler404 = 'freedom.views.defaults.page_not_found'
handler500 = 'freedom.views.defaults.server_error'


def include(arg, namespace=None, app_name=None):
    if isinstance(arg, tuple):
        # callable returning a namespace hint
        if namespace:
            raise ImproperlyConfigured('Cannot override the namespace for a dynamic module that provides a namespace')
        urlconf_module, app_name, namespace = arg
    else:
        # No namespace hint - use manually provided namespace
        urlconf_module = arg

    if isinstance(urlconf_module, six.string_types):
        urlconf_module = import_module(urlconf_module)
    patterns = getattr(urlconf_module, 'urlpatterns', urlconf_module)

    # Make sure we can iterate through the patterns (without this, some
    # testcases will break).
    if isinstance(patterns, (list, tuple)):
        for url_pattern in patterns:
            # Test if the LocaleRegexURLResolver is used within the include;
            # this should throw an error since this is not allowed!
            if isinstance(url_pattern, LocaleRegexURLResolver):
                raise ImproperlyConfigured(
                    'Using i18n_patterns in an included URLconf is not allowed.')

    return (urlconf_module, app_name, namespace)


def patterns(prefix, *args):
    warnings.warn(
        'freedom.conf.urls.patterns() is deprecated and will be removed in '
        'Freedom 2.0. Update your urlpatterns to be a list of '
        'freedom.conf.urls.url() instances instead.',
        RemovedInFreedom20Warning, stacklevel=2
    )
    pattern_list = []
    for t in args:
        if isinstance(t, (list, tuple)):
            t = url(prefix=prefix, *t)
        elif isinstance(t, RegexURLPattern):
            t.add_prefix(prefix)
        pattern_list.append(t)
    return pattern_list


def url(regex, view, kwargs=None, name=None, prefix=''):
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return RegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    else:
        if isinstance(view, six.string_types):
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % regex)
            if prefix:
                view = prefix + '.' + view
        return RegexURLPattern(regex, view, kwargs, name)
