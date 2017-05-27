import string
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.urls import (
    LocaleRegexURLResolver, RegexURLPattern, RegexURLResolver,
)
from django.utils.functional import lazy
from django.views import defaults

__all__ = ['handler400', 'handler403',
           'handler404', 'handler500', 'include', 'url']

handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler500 = defaults.server_error

DEFAULT_URL_CONTEXT = {
    'id': r'(?P<id>\d+)',
    'pk': r'(?P<pk>\d+)',
    'page': r'(?P<page>\d+)',
    'year': r'(?P<year>\d{4})',
    'month': r'(?P<month>(0?([1-9])|10|11|12))',
    'day': r'(?P<day>((0|1|2)?([1-9])|[1-3]0|31))',
    'date': (r'(?P<date>\d{4}-'
             '(0?([1-9])|10|11|12)-'
             '((0|1|2)?([1-9])|[1-3]0|31))'),
    'uuid': (r'(?P<uuid>'
             '[a-fA-F0-9]{8}-'
             '?[a-fA-F0-9]{4}-'
             '?[1345][a-fA-F0-9]{3}-'
             '?[a-fA-F0-9]{4}-'
             '?[a-fA-F0-9]{12})'),
}


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


class UrlPreprocessor:
    r"""Defines url preprocessor.

    Url preprocessor helps you to avoid lengthy regexps and regexp duplications.
    It also lets you use template strings syntax in url definitions.

    Example.
    Instead of this construction:
    url(r'^(?P<id>\d+)/(?P<year>\d{4})/(?P<month>(0?([1-9])|10|11|12))/$', view)

    You can use the following code:
    url(r'^$id/$year/$month/$', view)

    You can define your own url preprocessor in ``your_project.urls.py'' file:
    ``your_project.urls.py'':
    >>> from django.conf.urls import UrlPreprocessor, DEFAULT_URL_CONTEXT
    >>> url = UrlPreprocessor(DEFAULT_URL_CONTEXT)
    >>> url.update_url_context({
    ...     'chapter_id': r'(?P<chapter_id>ch\d{1,6})',
    ...     'book_id': r'(?P<book_id>\d+)'})
    ...
    >>> urlpatterns = [
    ...     url(r'^$book_id/$chapter_id/$', view),]
    ...
    [<RegexURLPattern None ^(?P<book_id>\d+)/(?P<chapter_id>ch\d{1,6})/$>]
    >>>

    """

    def __init__(self, url_context=None):
        self._url_context = {} if url_context is None else url_context.copy()
        self._lazy_formatter = lazy(
            lambda regex: self.formatter(str(regex)), str)

    def __call__(self, regex, view, kwargs=None, name=None):
        if isinstance(regex, str):
            regex = self.formatter(regex)
        else:
            regex = self._lazy_formatter(regex)
        return self._url(regex, view, kwargs, name)

    def formatter(self, regex):
        """Used for template formatting of a regular expression.

        Takes regular expression as an input and formats it according
        to preprocessor context.

        Uses ``string.Template'' formatter from standard library
        as a default one.

        """
        return string.Template(regex).safe_substitute(self._url_context)

    def update_url_context(self, context):
        self._url_context.update(context)

    def clear_url_context(self):
        self._url_context.clear()

    @staticmethod
    def _url(regex, view, kwargs=None, name=None):
        if isinstance(view, (list, tuple)):
            # For include(...) processing.
            urlconf_module, app_name, namespace = view
            return RegexURLResolver(
                regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
        elif callable(view):
            return RegexURLPattern(regex, view, kwargs, name)
        else:
            raise TypeError(
                'view must be a callable or a list/tuple in the case of include().')


url = UrlPreprocessor()
