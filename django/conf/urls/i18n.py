import warnings

from django.conf import settings
from django.conf.urls import patterns, url
from django.core.urlresolvers import LocaleRegexURLResolver
from django.utils import six
from django.utils.deprecation import RemovedInDjango110Warning
from django.views.i18n import set_language


def i18n_patterns(prefix, *args):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if isinstance(prefix, six.string_types):
        warnings.warn(
            "Calling i18n_patterns() with the `prefix` argument and with tuples "
            "instead of django.conf.urls.url() instances is deprecated and "
            "will no longer work in Django 1.10. Use a list of "
            "django.conf.urls.url() instances instead.",
            RemovedInDjango110Warning, stacklevel=2
        )
        pattern_list = patterns(prefix, *args)
    else:
        pattern_list = [prefix] + list(args)
    if not settings.USE_I18N:
        return pattern_list
    return [LocaleRegexURLResolver(pattern_list)]


urlpatterns = [
    url(r'^setlang/$', set_language, name='set_language'),
]
