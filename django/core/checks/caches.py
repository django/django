import pathlib

from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from django.core.cache.backends.filebased import FileBasedCache

from . import Error, Tags, Warning, register

E001 = Error(
    "You must define a '%s' cache in your CACHES setting." % DEFAULT_CACHE_ALIAS,
    id="caches.E001",
)


@register(Tags.caches)
def check_default_cache_is_configured(app_configs, **kwargs):
    if DEFAULT_CACHE_ALIAS not in settings.CACHES:
        return [E001]
    return []


@register(Tags.caches, deploy=True)
def check_cache_location_not_exposed(app_configs, **kwargs):
    cache = None
    alias_name = ""
    for alias, config in settings.CACHES.items():
        if config.get("BACKEND").endswith("FileBasedCache"):
            cache = caches[alias]
            alias_name = alias

    if cache is None:
        return []

    errors = []
    for name in ("MEDIA_ROOT", "STATIC_ROOT", "STATICFILES_DIRS"):
        setting = getattr(settings, name, None)
        if not setting:
            continue
        if name == "STATICFILES_DIRS":
            paths = set()
            for staticfiles_dir in setting:
                if isinstance(staticfiles_dir, (list, tuple)):
                    _, staticfiles_dir = staticfiles_dir
                paths.add(pathlib.Path(staticfiles_dir).resolve())
        else:
            paths = {pathlib.Path(setting).resolve()}

        check_result = FileBasedCache.check(cache, paths, name, alias_name)
        errors.append(check_result) if check_result else []

    return errors


@register(Tags.caches)
def check_file_based_cache_is_absolute(app_configs, **kwargs):
    alias_name = None
    location = None
    for alias, config in settings.CACHES.items():
        if config.get("BACKEND").endswith("FileBasedCache"):
            alias_name = alias
            location = config.get("LOCATION")

    if location is not None and not pathlib.Path(location).is_absolute():
        return [
            Warning(
                f"Your '{alias_name}' cache LOCATION path is relative. Use an "
                f"absolute path instead.",
                id="caches.W003",
            )
        ]

    return []
