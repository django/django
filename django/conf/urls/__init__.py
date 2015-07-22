import warnings
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.urls import (
    BaseResolver, LocalePrefix, LocalizedRegexPattern, RegexPattern, Resolver,
    ResolverEndpoint,
)
from django.utils import six
from django.utils.deprecation import (
    RemovedInDjango20Warning, RemovedInDjango110Warning,
)
from django.utils.functional import Promise

__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include', 'patterns', 'url']

handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


def include(arg, namespace=None, app_name=None):
    if app_name and not namespace:
        raise ValueError('Must specify a namespace if specifying app_name.')
    if app_name:
        warnings.warn(
            'The app_name argument to django.conf.urls.include() is deprecated. '
            'Set the app_name in the included URLconf instead.',
            RemovedInDjango20Warning, stacklevel=2
        )

    if isinstance(arg, tuple):
        # callable returning a namespace hint
        try:
            urlconf_module, app_name = arg
        except ValueError:
            if namespace:
                raise ImproperlyConfigured(
                    'Cannot override the namespace for a dynamic module that provides a namespace'
                )
            warnings.warn(
                'Passing a 3-tuple to django.conf.urls.include() is deprecated. '
                'Pass a 2-tuple containing the list of patterns and app_name, '
                'and provide the namespace argument to include() instead.',
                RemovedInDjango20Warning, stacklevel=2
            )
            urlconf_module, app_name, namespace = arg
    else:
        # No namespace hint - use manually provided namespace
        urlconf_module = arg

    if isinstance(urlconf_module, six.string_types):
        urlconf_module = import_module(urlconf_module)
    patterns = getattr(urlconf_module, 'urlpatterns', urlconf_module)
    app_name = getattr(urlconf_module, 'app_name', app_name)
    if namespace and not app_name:
        warnings.warn(
            'Specifying a namespace in django.conf.urls.include() without '
            'providing an app_name is deprecated. Set the app_name attribute '
            'in the included module, or pass a 2-tuple containing the list of '
            'patterns and app_name instead.',
            RemovedInDjango20Warning, stacklevel=2
        )

    namespace = namespace or app_name

    # Make sure we can iterate through the patterns (without this, some
    # testcases will break).
    if isinstance(patterns, (list, tuple)):
        for name, resolver in patterns:
            # Test if the LocaleRegexURLResolver is used within the include;
            # this should throw an error since this is not allowed!
            if any(isinstance(constraint, LocalePrefix) for constraint in resolver.constraints):
                raise ImproperlyConfigured(
                    'Using i18n_patterns in an included URLconf is not allowed.')

    return (urlconf_module, app_name, namespace)


def patterns(prefix, *args):
    warnings.warn(
        'django.conf.urls.patterns() is deprecated and will be removed in '
        'Django 1.10. Update your urlpatterns to be a list of '
        'django.conf.urls.url() instances instead.',
        RemovedInDjango110Warning, stacklevel=2
    )
    pattern_list = []
    for t in args:
        if isinstance(t, (list, tuple)):
            if len(t) != 2 or not isinstance(t[1], BaseResolver):
                t = url(prefix=prefix, *t)
            elif len(t) == 2 and isinstance(t[1], ResolverEndpoint):
                t[1].add_prefix(prefix)
        pattern_list.append(t)
    return pattern_list


def url(constraints, view, kwargs=None, name=None, prefix='', decorators=None):
    if isinstance(constraints, six.string_types):
        constraints = RegexPattern(constraints)
    elif isinstance(constraints, Promise):
        constraints = LocalizedRegexPattern(constraints)
    if not isinstance(constraints, (list, tuple)):
        constraints = [constraints]

    if isinstance(view, (list, tuple)):
        resolvers, app_name, namespace = view
        return namespace, Resolver(resolvers, app_name, constraints=constraints, kwargs=kwargs, decorators=decorators)
    else:
        if isinstance(view, six.string_types):
            warnings.warn(
                'Support for string view arguments to url() is deprecated and '
                'will be removed in Django 2.0 (got %s). Pass the callable '
                'instead.' % view,
                RemovedInDjango110Warning, stacklevel=2
            )
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % constraints)
            if prefix:
                view = prefix + '.' + view
        return None, ResolverEndpoint(view, name, constraints=constraints, kwargs=kwargs, decorators=decorators)
