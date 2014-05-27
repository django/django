import warnings

from freedom.conf import settings
from freedom.conf.urls import patterns, url
from freedom.core.urlresolvers import LocaleRegexURLResolver
from freedom.utils import six
from freedom.utils.deprecation import RemovedInFreedom20Warning


def i18n_patterns(prefix, *args):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if isinstance(prefix, six.string_types):
        warnings.warn(
            "Calling i18n_patterns() with the `prefix` argument and with tuples "
            "instead of freedom.conf.urls.url() instances is deprecated and "
            "will no longer work in Freedom 2.0. Use a list of "
            "freedom.conf.urls.url() instances instead.",
            RemovedInFreedom20Warning, stacklevel=2
        )
        pattern_list = patterns(prefix, *args)
    else:
        pattern_list = [prefix] + list(args)
    if not settings.USE_I18N:
        return pattern_list
    return [LocaleRegexURLResolver(pattern_list)]


urlpatterns = [
    url(r'^setlang/$', 'freedom.views.i18n.set_language', name='set_language'),
]
