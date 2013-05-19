from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_by_path

from django.contrib.formtools.wizard.storage.base import BaseStorage
from django.contrib.formtools.wizard.storage.exceptions import (
    MissingStorage, NoFileStorageConfigured)


def get_storage(path, *args, **kwargs):
    try:
        storage_class = import_by_path(path)
    except ImproperlyConfigured as e:
        raise MissingStorage('Error loading storage: %s' % e)
    return storage_class(*args, **kwargs)
