from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module


def get_storage(import_path):
    """
    Imports the message storage class described by import_path, where
    import_path is the full Python path to the class.
    """
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a Python path." % import_path)
    module, classname = import_path[:dot], import_path[dot + 1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                   (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '
                                   'class.' % (module, classname))


# Callable with the same interface as the storage classes i.e.  accepts a
# 'request' object.  It is wrapped in a lambda to stop 'settings' being used at
# the module level
default_storage = lambda request: get_storage(settings.MESSAGE_STORAGE)(request)
