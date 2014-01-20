from django.utils.module_loading import import_string

from django.contrib.formtools.wizard.storage.base import BaseStorage
from django.contrib.formtools.wizard.storage.exceptions import (
    MissingStorage, NoFileStorageConfigured)

__all__ = [
    "BaseStorage", "MissingStorage", "NoFileStorageConfigured", "get_storage",
]


def get_storage(path, *args, **kwargs):
    try:
        storage_class = import_string(path)
    except ImportError as e:
        raise MissingStorage('Error loading storage: %s' % e)
    return storage_class(*args, **kwargs)
