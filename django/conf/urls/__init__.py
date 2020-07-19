import warnings

from django.urls import include, re_path
from django.utils.deprecation import RemovedInDjango40Warning
from django.views import defaults

__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include', 'url']

handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler500 = defaults.server_error


def url(regex, view, kwargs=None, name=None):
    warnings.warn(
        'django.conf.urls.url() is deprecated in favor of '
        'django.urls.re_path().',
        RemovedInDjango40Warning,
        stacklevel=2,
    )
    return re_path(regex, view, kwargs, name)
