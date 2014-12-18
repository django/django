import warnings
from functools import wraps
from django.utils.deprecation import RemovedInDjango20Warning


class ConfList(list):
    """
    Backward compatibility shim to convert global settings
    tuples to lists.
    """

    def tuple_warn(tuple_op, list_op=None):
        """
        Warns about the conversion of the settings to lists, and fall back
        to the specified tuple method.
        """
        list_op = list_op or tuple_op

        def operator(self, other):
            """
            A generic binary operator.
            """
            if isinstance(other, tuple):
                warnings.warn('Global settings have been converted to lists.',
                              RemovedInDjango20Warning, 2)
                return getattr(tuple(self), tuple_op)(other)
            return getattr(list(self), list_op)(other)

        return operator

    __add__ = tuple_warn('__add__')
    __iadd__ = tuple_warn('__add__', '__iadd__')

    __eq__ = tuple_warn('__eq__')
    __ne__ = tuple_warn('__ne__')
    __lt__ = tuple_warn('__lt__')
    __gt__ = tuple_warn('__gt__')
    __lte__ = tuple_warn('__lte__')
    __gte__ = tuple_warn('__gte__')

    def __mul__(self, other):
        # Multiplication gives no indication of whether it's a tuple
        # expected or a list, so we must put off guessing.
        return type(self)(super(ConfList, self).__mul__(other))

    __rmul__ = __mul__
    __imul__ = __mul__
