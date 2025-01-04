from django.utils.version import PY313

if PY313:
    from copy import replace
else:
    # Backport of copy.replace() from Python 3.13.
    def replace(obj, /, **changes):
        """Return a new object replacing specified fields with new values.

        This is especially useful for immutable objects, like named tuples or
        frozen dataclasses.
        """
        cls = obj.__class__
        func = getattr(cls, "__replace__", None)
        if func is None:
            raise TypeError(f"replace() does not support {cls.__name__} objects")
        return func(obj, **changes)
