import warnings

from django.conf import DEFAULT_STORAGE_ALIAS, settings
from django.utils.deprecation import RemovedInDjango51Warning
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from .base import Storage
from .filesystem import FileSystemStorage
from .handler import InvalidStorageError, StorageHandler
from .memory import InMemoryStorage

__all__ = (
    "FileSystemStorage",
    "InMemoryStorage",
    "Storage",
    "DefaultStorage",
    "default_storage",
    "get_storage_class",
    "InvalidStorageError",
    "StorageHandler",
    "storages",
)

GET_STORAGE_CLASS_DEPRECATED_MSG = (
    "django.core.files.storage.get_storage_class is deprecated in favor of "
    "using django.core.files.storage.storages."
)


def get_storage_class(import_path=None):
    warnings.warn(
        GET_STORAGE_CLASS_DEPRECATED_MSG,
        RemovedInDjango51Warning,
        stacklevel=2,
    )
    return import_string(import_path or settings.DEFAULT_FILE_STORAGE)


class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = storages[DEFAULT_STORAGE_ALIAS]


storages = StorageHandler()
default_storage = DefaultStorage()
