"""Functions for use in URLsconfs."""

from functools import partial
from typing import Union, Tuple, Callable, Dict, Optional, List
from django.core.exceptions import ImproperlyConfigured
from .resolvers import (
    LocalePrefixPattern,
    RegexPattern,
    RoutePattern,
    URLPattern,
    URLResolver,
)


def include(arg: Union[str, Tuple], namespace: Optional[str] = None) -> Tuple:
    """
    Include another URLconf module, optionally providing a namespace.

    :param arg: A string or a tuple containing the URLconf module and an optional app_name.
    :param namespace: An optional namespace for the included URLconf.
    :return: A tuple containing the URLconf module, app_name, and namespace.
    :raises ImproperlyConfigured: If the provided arguments are invalid.
    """
    app_name = None
    if isinstance(arg, tuple):
        # Callable returning a namespace hint.
        try:
            urlconf_module, app_name = arg
        except ValueError:
            raise ImproperlyConfigured(
                "Passing a %d-tuple to include() is not supported. Pass a "
                "2-tuple containing the list of patterns and app_name, and "
                "provide the namespace argument to include() instead." % len(arg)
            )
        if namespace:
            raise ImproperlyConfigured(
                "Cannot override the namespace for a dynamic module that "
                "provides a namespace."
            )
    else:
        # No namespace hint - use manually provided namespace.
        urlconf_module = arg

    if isinstance(urlconf_module, str):
        from importlib import import_module
        urlconf_module = import_module(urlconf_module)
        
    patterns = getattr(urlconf_module, "urlpatterns", urlconf_module)
    app_name = getattr(urlconf_module, "app_name", app_name)
    if namespace and not app_name:
        raise ImproperlyConfigured(
            "Specifying a namespace in include() without providing an app_name "
            "is not supported. Set the app_name attribute in the included "
            "module, or pass a 2-tuple containing the list of patterns and "
            "app_name instead.",
        )
    namespace = namespace or app_name
    # Make sure the patterns can be iterated through (without this, some
    # test cases will break).
    if isinstance(patterns, (list, tuple)):
        for url_pattern in patterns:
            pattern = getattr(url_pattern, "pattern", None)
            if isinstance(pattern, LocalePrefixPattern):
                raise ImproperlyConfigured(
                    "Using i18n_patterns in an included URLconf is not allowed."
                )
    return (urlconf_module, app_name, namespace)


def _path(
    route: str,
    view: Union[Callable, List, Tuple],
    kwargs: Optional[Dict] = None,
    name: Optional[str] = None,
    Pattern: type = RoutePattern
) -> Union[URLPattern, URLResolver]:
    """
    Create a URL pattern or resolver.

    :param route: The URL pattern as a string.
    :param view: The view function or a list/tuple for include().
    :param kwargs: Additional arguments to pass to the view.
    :param name: The name of the URL pattern.
    :param Pattern: The pattern class to use (RoutePattern or RegexPattern).
    :return: A URLPattern or URLResolver instance.
    :raises TypeError: If the arguments are of incorrect types.
    """
    from django.views import View

    if kwargs is not None and not isinstance(kwargs, dict):
        raise TypeError(
            f"kwargs argument must be a dict, but got {kwargs.__class__.__name__}."
        )
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        pattern = Pattern(route, is_endpoint=False)
        urlconf_module, app_name, namespace = view
        return URLResolver(
            pattern,
            urlconf_module,
            kwargs,
            app_name=app_name,
            namespace=namespace,
        )
    elif callable(view):
        pattern = Pattern(route, name=name, is_endpoint=True)
        return URLPattern(pattern, view, kwargs, name)
    elif isinstance(view, View):
        view_cls_name = view.__class__.__name__
        raise TypeError(
            f"view must be a callable, pass {view_cls_name}.as_view(), not "
            f"{view_cls_name}()."
        )
    else:
        raise TypeError(
            "view must be a callable or a list/tuple in the case of include()."
        )


path = partial(_path, Pattern=RoutePattern)
re_path = partial(_path, Pattern=RegexPattern)

