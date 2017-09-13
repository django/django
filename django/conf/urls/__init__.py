from django.urls import RegexURLPattern, RegexURLResolver, include
from django.views import defaults

__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include', 'url']

handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler500 = defaults.server_error


def url(regex, view, kwargs=None, name=None):
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return RegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    elif callable(view):
        return RegexURLPattern(regex, view, kwargs, name)
    else:
        raise TypeError('view must be a callable or a list/tuple in the case of include().')
