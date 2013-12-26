from django.conf import settings
from django.utils.module_loading import import_by_path


def default_storage(request):
    """
    Callable with the same interface as the storage classes.

    This isn't just default_storage = import_by_path(settings.MESSAGE_STORAGE)
    to avoid accessing the settings at the module level.
    """
    return import_by_path(settings.MESSAGE_STORAGE)(request)
