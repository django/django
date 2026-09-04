from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS, caches

from . import Error, Tags, register

E001 = Error(
    "You must define a '%s' cache in your CACHES setting." % DEFAULT_CACHE_ALIAS,
    id="caches.E001",
)


@register(Tags.caches)
def check_default_cache_is_configured(app_configs, **kwargs):
    if DEFAULT_CACHE_ALIAS not in settings.CACHES:
        return [E001]
    return []


@register(Tags.caches)
def check_all_caches(app_configs, **kwargs):
    errors = []
    for alias, config in settings.CACHES.items():
        cache = caches[alias]
        errors.extend(cache.check(alias=alias, config=config))
    return errors
