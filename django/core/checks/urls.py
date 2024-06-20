import inspect
from collections import Counter

from django.conf import settings
from django.core.exceptions import ViewDoesNotExist

from . import Error, Tags, Warning, register


@register(Tags.urls)
def check_url_config(app_configs, **kwargs):
    if getattr(settings, "ROOT_URLCONF", None):
        from django.urls import get_resolver

        resolver = get_resolver()
        return check_resolver(resolver)
    return []


def check_resolver(resolver):
    """
    Recursively check the resolver.
    """
    check_method = getattr(resolver, "check", None)
    if check_method is not None:
        return check_method()
    elif not hasattr(resolver, "resolve"):
        return get_warning_for_invalid_pattern(resolver)
    else:
        return []


@register(Tags.urls)
def check_url_namespaces_unique(app_configs, **kwargs):
    """
    Warn if URL namespaces used in applications aren't unique.
    """
    if not getattr(settings, "ROOT_URLCONF", None):
        return []

    from django.urls import get_resolver

    resolver = get_resolver()
    all_namespaces = _load_all_namespaces(resolver)
    counter = Counter(all_namespaces)
    non_unique_namespaces = [n for n, count in counter.items() if count > 1]
    errors = []
    for namespace in non_unique_namespaces:
        errors.append(
            Warning(
                "URL namespace '{}' isn't unique. You may not be able to reverse "
                "all URLs in this namespace".format(namespace),
                id="urls.W005",
            )
        )
    return errors


def _load_all_namespaces(resolver, parents=()):
    """
    Recursively load all namespaces from URL patterns.
    """
    url_patterns = getattr(resolver, "url_patterns", [])
    namespaces = [
        ":".join(parents + (url.namespace,))
        for url in url_patterns
        if getattr(url, "namespace", None) is not None
    ]
    for pattern in url_patterns:
        namespace = getattr(pattern, "namespace", None)
        current = parents
        if namespace is not None:
            current += (namespace,)
        namespaces.extend(_load_all_namespaces(pattern, current))
    return namespaces


def get_warning_for_invalid_pattern(pattern):
    """
    Return a list containing a warning that the pattern is invalid.

    describe_pattern() cannot be used here, because we cannot rely on the
    urlpattern having regex or name attributes.
    """
    if isinstance(pattern, str):
        hint = (
            "Try removing the string '{}'. The list of urlpatterns should not "
            "have a prefix string as the first element.".format(pattern)
        )
    elif isinstance(pattern, tuple):
        hint = "Try using path() instead of a tuple."
    else:
        hint = None

    return [
        Error(
            "Your URL pattern {!r} is invalid. Ensure that urlpatterns is a list "
            "of path() and/or re_path() instances.".format(pattern),
            hint=hint,
            id="urls.E004",
        )
    ]


@register(Tags.urls)
def check_url_settings(app_configs, **kwargs):
    errors = []
    for name in ("STATIC_URL", "MEDIA_URL"):
        value = getattr(settings, name)
        if value and not value.endswith("/"):
            errors.append(E006(name))
    return errors


def E006(name):
    return Error(
        "The {} setting must end with a slash.".format(name),
        id="urls.E006",
    )


@register(Tags.urls)
def check_custom_error_handlers(app_configs, **kwargs):
    if not getattr(settings, "ROOT_URLCONF", None):
        return []

    from django.urls import get_resolver

    resolver = get_resolver()

    errors = []
    # All handlers take (request, exception) arguments except handler500
    # which takes (request).
    for status_code, num_parameters in [(400, 2), (403, 2), (404, 2), (500, 1)]:
        try:
            handler = resolver.resolve_error_handler(status_code)
        except (ImportError, ViewDoesNotExist) as e:
            path = getattr(resolver.urlconf_module, "handler%s" % status_code)
            msg = (
                "The custom handler{status_code} view '{path}' could not be "
                "imported."
            ).format(status_code=status_code, path=path)
            errors.append(Error(msg, hint=str(e), id="urls.E008"))
            continue
        signature = inspect.signature(handler)
        args = [None] * num_parameters
        try:
            signature.bind(*args)
        except TypeError:
            msg = (
                "The custom handler{status_code} view '{path}' does not "
                "take the correct number of arguments ({args})."
            ).format(
                status_code=status_code,
                path=handler.__module__ + "." + handler.__qualname__,
                args="request, exception" if num_parameters == 2 else "request",
            )
            errors.append(Error(msg, id="urls.E007"))
    return errors
