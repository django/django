from django.conf import settings
from django.conf.urls import url
from django.urls import LocaleRegexURLResolver
from django.views.i18n import set_language


def i18n_patterns(*urls):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if not settings.USE_I18N:
        return urls
    return [LocaleRegexURLResolver(list(urls))]


urlpatterns = [
    url(r'^setlang/$', set_language, name='set_language'),
]
