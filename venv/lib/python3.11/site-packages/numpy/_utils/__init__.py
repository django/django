"""
This is a module for defining private helpers which do not depend on the
rest of NumPy.

Everything in here must be self-contained so that it can be
imported anywhere else without creating circular imports.
If a utility requires the import of NumPy, it probably belongs
in ``numpy.core``.
"""

from ._convertions import asunicode, asbytes


def set_module(module):
    """Private decorator for overriding __module__ on a function or class.

    Example usage::

        @set_module('numpy')
        def example():
            pass

        assert example.__module__ == 'numpy'
    """
    def decorator(func):
        if module is not None:
            func.__module__ = module
        return func
    return decorator
