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
            return (
                path or '%s.%s' % (obj.__class__.__module__, obj.__class__.__name__),
                obj._constructor_args[0],
                obj._constructor_args[1],
            )

        klass.__new__ = staticmethod(__new__)
        klass.deconstruct = deconstruct

        return klass

    if not args:
        return decorator
    return decorator(*args, **kwargs)
