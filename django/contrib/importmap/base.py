import functools
from importlib import import_module

from django.utils.module_loading import module_has_submodule

IMPORTMAP_MODULE_NAME = "importmap"


@functools.cache
def get_importmaps():
    from django.apps import apps

    result = {}

    for label, app_config in apps.app_configs.items():
        if not module_has_submodule(app_config.module, IMPORTMAP_MODULE_NAME):
            continue

        importmap = import_module("%s.%s" % (app_config.module, IMPORTMAP_MODULE_NAME))
        importmap = getattr(importmap, IMPORTMAP_MODULE_NAME, {})
        result[label] = importmap

    return result
