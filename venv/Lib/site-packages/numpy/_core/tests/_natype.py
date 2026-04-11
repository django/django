# Vendored implementation of pandas.NA, adapted from pandas/_libs/missing.pyx
#
# This is vendored to avoid adding pandas as a test dependency.

__all__ = ["pd_NA"]

import numbers

import numpy as np


def _create_binary_propagating_op(name, is_divmod=False):
    is_cmp = name.strip("_") in ["eq", "ne", "le", "lt", "ge", "gt"]

    def method(self, other):
        if (
            other is pd_NA
            or isinstance(other, (str, bytes, numbers.Number, np.bool))
            or (isinstance(other, np.ndarray) and not other.shape)
        ):
            # Need the other.shape clause to handle NumPy scalars,
            # since we do a setitem on `out` below, which
            # won't work for NumPy scalars.
            if is_divmod:
                return pd_NA, pd_NA
            else:
                return pd_NA

        elif isinstance(other, np.ndarray):
            out = np.empty(other.shape, dtype=object)
            out[:] = pd_NA

            if is_divmod:
                return out, out.copy()
            else:
                return out

        elif is_cmp and isinstance(other, (np.datetime64, np.timedelta64)):
            return pd_NA

        elif isinstance(other, np.datetime64):
            if name in ["__sub__", "__rsub__"]:
                return pd_NA

        elif isinstance(other, np.timedelta64):
            if name in ["__sub__", "__rsub__", "__add__", "__radd__"]:
                return pd_NA

        return NotImplemented

    method.__name__ = name
    return method


def _create_unary_propagating_op(name: str):
    def method(self):
        return pd_NA

    method.__name__ = name
    return method


class NAType:
    def __repr__(self) -> str:
        return "<NA>"

    def __format__(self, format_spec) -> str:
        try:
            return self.__repr__().__format__(format_spec)
        except ValueError:
            return self.__repr__()

    def __bool__(self):
        raise TypeError("boolean value of NA is ambiguous")

    def __hash__(self):
        return 2**61 - 1

    def __reduce__(self):
        return "pd_NA"

    # Binary arithmetic and comparison ops -> propagate

    __add__ = _create_binary_propagating_op("__add__")
    __radd__ = _create_binary_propagating_op("__radd__")
    __sub__ = _create_binary_propagating_op("__sub__")
    __rsub__ = _create_binary_propagating_op("__rsub__")
    __mul__ = _create_binary_propagating_op("__mul__")
    __rmul__ = _create_binary_propagating_op("__rmul__")
    __matmul__ = _create_binary_propagating_op("__matmul__")
    __rmatmul__ = _create_binary_propagating_op("__rmatmul__")
    __truediv__ = _create_binary_propagating_op("__truediv__")
    __rtruediv__ = _create_binary_propagating_op("__rtruediv__")
    __floordiv__ = _create_binary_propagating_op("__floordiv__")
    __rfloordiv__ = _create_binary_propagating_op("__rfloordiv__")
    __mod__ = _create_binary_propagating_op("__mod__")
    __rmod__ = _create_binary_propagating_op("__rmod__")
    __divmod__ = _create_binary_propagating_op("__divmod__", is_divmod=True)
    __rdivmod__ = _create_binary_propagating_op("__rdivmod__", is_divmod=True)
    # __lshift__ and __rshift__ are not implemented

    __eq__ = _create_binary_propagating_op("__eq__")
    __ne__ = _create_binary_propagating_op("__ne__")
    __le__ = _create_binary_propagating_op("__le__")
    __lt__ = _create_binary_propagating_op("__lt__")
    __gt__ = _create_binary_propagating_op("__gt__")
    __ge__ = _create_binary_propagating_op("__ge__")

    # Unary ops

    __neg__ = _create_unary_propagating_op("__neg__")
    __pos__ = _create_unary_propagating_op("__pos__")
    __abs__ = _create_unary_propagating_op("__abs__")
    __invert__ = _create_unary_propagating_op("__invert__")

    # Logical ops using Kleene logic

    def __and__(self, other):
        if other is False:
            return False
        elif other is True or other is pd_NA:
            return pd_NA
        return NotImplemented

    __rand__ = __and__

    def __or__(self, other):
        if other is True:
            return True
        elif other is False or other is pd_NA:
            return pd_NA
        return NotImplemented

    __ror__ = __or__

    def __xor__(self, other):
        if other is False or other is True or other is pd_NA:
            return pd_NA
        return NotImplemented

    __rxor__ = __xor__


pd_NA = NAType()
