import functools

from django.conf import settings
from django.conf.urls import url
from django.urls import LocaleRegexURLResolver, get_resolver
from django.views.i18n import set_language


def i18n_patterns(*urls, **kwargs):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if not settings.USE_I18N:
        return list(urls)
    prefix_default_language = kwargs.pop('prefix_default_language', True)
    assert not kwargs, 'Unexpected kwargs for i18n_patterns(): %s' % kwargs
    return [LocaleRegexURLResolver(list(urls), prefix_default_language=prefix_default_language)]


@functools.lru_cache(maxsize=None)
def is_language_prefix_patterns_used(urlconf):
    """
    Return a tuple of two booleans: (
        `True` if LocaleRegexURLResolver` is used in the `urlconf`,
        `True` if the default language should be prefixed
    )
    """
    for url_pattern in get_resolver(urlconf).url_patterns:
        if isinstance(url_pattern, LocaleRegexURLResolver):
            return True, url_pattern.prefix_default_language
    return False, False


urlpatterns = [
    url(r'^setlang/$', set_language, name='set_language'),
]
