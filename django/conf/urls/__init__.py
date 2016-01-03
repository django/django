import functools
import warnings
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import Promise, cached_property

__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include', 'url']

handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


def include(arg, namespace=None, app_name=None):
    from django.urls import LocalePrefix

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
    urlpatterns = getattr(urlconf_module, 'urlpatterns', urlconf_module)
    app_name = getattr(urlconf_module, 'app_name', app_name)
    namespace = namespace or app_name

    if namespace and not app_name:
        warnings.warn(
            'Specifying a namespace in django.conf.urls.include() without '
            'providing an app_name is deprecated. Set the app_name attribute '
            'in the included module, or pass a 2-tuple containing the list of '
            'patterns and app_name instead.',
            RemovedInDjango20Warning, stacklevel=2
        )

    # Make sure we can iterate through the patterns (without this, some
    # testcases will break).
    if isinstance(urlpatterns, (list, tuple)):
        for urlpattern in urlpatterns:
            # Test if the LocaleRegexURLResolver is used within the include;
            # this should throw an error since this is not allowed!
            if any(isinstance(constraint, LocalePrefix) for constraint in urlpattern.constraints):
                raise ImproperlyConfigured('Using i18n_patterns in an included URLconf is not allowed.')

    return urlconf_module, app_name, namespace


def url(regex, view, kwargs=None, name=None, decorators=None, resolver_cls=None):
    from django.urls import RegexPattern, LocalizedRegexPattern

    if isinstance(regex, six.string_types):
        regex = RegexPattern(regex)
    elif isinstance(regex, Promise):
        regex = LocalizedRegexPattern(regex)

    if not isinstance(regex, (list, tuple)):
        constraints = [regex]
    else:
        constraints = regex

    if isinstance(view, (list, tuple)):
        return URLPattern(constraints, URLConf(*view, kwargs=kwargs, decorators=decorators, resolver_cls=resolver_cls))
    elif callable(view):
        return URLPattern(constraints, Endpoint(view, name, kwargs, decorators, resolver_cls))
    else:
        raise TypeError('view must be a callable or a list/tuple in the case of include().')


class Endpoint(object):
    def __init__(self, view, url_name=None, kwargs=None, decorators=None, resolver_cls=None):
        self.view = view
        self.url_name = url_name
        self.kwargs = kwargs or {}
        self.decorators = list(decorators) if decorators is not None else []
        self._resolver_cls = resolver_cls

    @cached_property
    def lookup_str(self):
        """
        A string that identifies the view (e.g. 'path.to.view_function' or
        'path.to.ClassBasedView').
        """
        func = self.view
        if isinstance(func, functools.partial):
            func = func.func
        if not hasattr(func, '__name__'):
            return func.__module__ + "." + func.__class__.__name__
        else:
            return func.__module__ + "." + func.__name__

    @cached_property
    def resolver_cls(self):
        from django.urls import ResolverEndpoint
        return self._resolver_cls or ResolverEndpoint


class URLPattern(object):
    def __init__(self, constraints, target):
        self.constraints = constraints
        self.target = target

    def is_endpoint(self):
        return isinstance(self.target, Endpoint)

    def as_resolver(self, **kwargs):
        cls = self.target.resolver_cls
        return cls(self, **kwargs)


class URLConf(object):
    def __init__(self, urlconf, app_name=None, namespace=None, kwargs=None, decorators=None, resolver_cls=None):
        self.urlconf_name = urlconf
        self.app_name = app_name
        self.namespace = namespace
        self.kwargs = kwargs or {}
        self._decorators = decorators or []
        self._resolver_cls = resolver_cls

    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf_name, six.string_types):
            return import_module(self.urlconf_name)
        else:
            return self.urlconf_name

    @property
    def urlpatterns(self):
        urlpatterns = getattr(self.urlconf_module, 'urlpatterns', self.urlconf_module)
        try:
            iter(urlpatterns)
        except TypeError:
            msg = (
                "The included URLconf '{name}' does not appear to have any "
                "patterns in it. If you see valid patterns in the file then "
                "the issue is probably caused by a circular import."
            )
            raise ImproperlyConfigured(msg.format(name=self.urlconf_name))
        return urlpatterns

    @cached_property
    def decorators(self):
        return self._decorators + getattr(self.urlconf_module, 'decorators', [])

    @cached_property
    def resolver_cls(self):
        from django.urls import Resolver
        return self._resolver_cls or getattr(self.urlconf_module, 'resolver_cls', Resolver)
