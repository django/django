from django.utils.importlib import import_module

from django.contrib.formtools.wizard.storage.base import BaseStorage
from django.contrib.formtools.wizard.storage.exceptions import (
    MissingStorageModule, MissingStorageClass, NoFileStorageConfigured)


def get_storage(path, *args, **kwargs):
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise MissingStorageModule(
            'Error loading storage %s: "%s"' % (module, e))
    try:
        storage_class = getattr(mod, attr)
    except AttributeError:
        raise MissingStorageClass(
            'Module "%s" does not define a storage named "%s"' % (module, attr))
    return storage_class(*args, **kwargs)

