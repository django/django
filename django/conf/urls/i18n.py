from django.conf import settings
from django.conf.urls import url
from django.core.urlresolvers import LocaleRegexURLResolver
from django.views.i18n import set_language


def i18n_patterns(*urls, prefix_default_language=True):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if not settings.USE_I18N:
        return urls
    return [LocaleRegexURLResolver(
        list(urls),
        prefix_default_language=prefix_default_language,
    )]


urlpatterns = [
    url(r'^setlang/$', set_language, name='set_language'),
]
