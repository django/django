from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.urls import (
    LocaleRegexURLResolver, RegexURLPattern, RegexURLResolver,
)
from django.views import defaults

__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include', 'url']

handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler500 = defaults.server_error


def include(arg, namespace=None):
    app_name = None
    if isinstance(arg, tuple):
        # callable returning a namespace hint
        try:
            urlconf_module, app_name = arg
        except ValueError:
            if namespace:
                raise ImproperlyConfigured(
                    'Cannot override the namespace for a dynamic module that '
                    'provides a namespace.'
                )
            raise ImproperlyConfigured(
                'Passing a %d-tuple to django.conf.urls.include() is not supported. '
                'Pass a 2-tuple containing the list of patterns and app_name, '
                'and provide the namespace argument to include() instead.' % len(arg)
            )
    else:
        # No namespace hint - use manually provided namespace
        urlconf_module = arg

    if isinstance(urlconf_module, str):
        urlconf_module = import_module(urlconf_module)
    patterns = getattr(urlconf_module, 'urlpatterns', urlconf_module)
    app_name = getattr(urlconf_module, 'app_name', app_name)
    if namespace and not app_name:
        raise ImproperlyConfigured(
            'Specifying a namespace in django.conf.urls.include() without '
            'providing an app_name is not supported. Set the app_name attribute '
            'in the included module, or pass a 2-tuple containing the list of '
            'patterns and app_name instead.',
        )

    namespace = namespace or app_name

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


def url(regex, view, kwargs=None, name=None):
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return RegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    elif callable(view):
        return RegexURLPattern(regex, view, kwargs, name)
    else:
        raise TypeError('view must be a callable or a list/tuple in the case of include().')
