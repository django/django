from __future__ import unicode_literals

from importlib import import_module

from django.conf import settings
from django.conf.urls import URLConf, URLPattern, url
from django.urls import LocalePrefix
from django.utils import lru_cache
from django.views.i18n import set_language


def i18n_patterns(*urls, **kwargs):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if not settings.USE_I18N:
        return urls
    prefix_default_language = kwargs.pop('prefix_default_language', True)
    assert not kwargs, 'Unexpected kwargs for i18n_patterns(): %s' % kwargs
    return [URLPattern([LocalePrefix(prefix_default_language)], URLConf(urls))]


@lru_cache.lru_cache(maxsize=None)
def is_language_prefix_patterns_used(urlconf):
    """
    Return a tuple of two booleans: (
        `True` if `i18n_patterns()` is used in the `urlconf`,
        `True` if the default language should be prefixed
    )
    """
    urlconf_module = import_module(urlconf)
    for urlpattern in urlconf_module.urlpatterns:
        for constraint in urlpattern.constraints:
            if isinstance(constraint, LocalePrefix):
                return True, constraint.prefix_default_language
    return False, False


urlpatterns = [
    url(r'^setlang/$', set_language, name='set_language'),
]
