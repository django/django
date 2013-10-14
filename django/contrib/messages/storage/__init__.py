from django.conf import settings
from django.utils.module_loading import import_by_path as get_storage


# Callable with the same interface as the storage classes i.e.  accepts a
# 'request' object.  It is wrapped in a lambda to stop 'settings' being used at
# the module level
default_storage = lambda request: get_storage(settings.MESSAGE_STORAGE)(request)
