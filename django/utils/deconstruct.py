from __future__ import absolute_import  # Avoid importing `importlib` from this package.
from importlib import import_module


def deconstructible(*args, **kwargs):
    """
    Class decorator that allow the decorated class to be serialized
    by the migrations subsystem.

    Accepts an optional kwarg `path` to specify the import path.
    """
    path = kwargs.pop('path', None)

    def decorator(klass):
        def __new__(cls, *args, **kwargs):
            # We capture the arguments to make returning them trivial
            obj = super(klass, cls).__new__(cls)
            obj._constructor_args = (args, kwargs)
            return obj

        def deconstruct(obj):
            """
            Returns a 3-tuple of class import path, positional arguments,
            and keyword arguments.
            """
            # Python 2/fallback version
            if path:
                module_name, _, name = path.rpartition('.')
            else:
                module_name = obj.__module__
                name = obj.__class__.__name__
            # Make sure it's actually there and not an inner class
            module = import_module(module_name)
            if not hasattr(module, name):
                raise ValueError(
                    "Could not find object %s in %s.\n"
                    "Please note that you cannot serialize things like inner "
                    "classes. Please move the object into the main module "
                    "body to use migrations.\n"
                    "For more information, see "
                    "https://docs.djangoproject.com/en/dev/topics/migrations/#serializing-values"
                    % (name, module_name))
            return (
                path or '%s.%s' % (obj.__class__.__module__, name),
                obj._constructor_args[0],
                obj._constructor_args[1],
            )

        klass.__new__ = staticmethod(__new__)
        klass.deconstruct = deconstruct

        return klass

    if not args:
        return decorator
    return decorator(*args, **kwargs)
