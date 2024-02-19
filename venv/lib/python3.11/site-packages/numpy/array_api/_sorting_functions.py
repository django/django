from __future__ import annotations

from ._array_object import Array
from ._dtypes import _real_numeric_dtypes

import numpy as np


# Note: the descending keyword argument is new in this function
def argsort(
    x: Array, /, *, axis: int = -1, descending: bool = False, stable: bool = True
) -> Array:
    """
    Array API compatible wrapper for :py:func:`np.argsort <numpy.argsort>`.

    See its docstring for more information.
    """
    if x.dtype not in _real_numeric_dtypes:
        raise TypeError("Only real numeric dtypes are allowed in argsort")
    # Note: this keyword argument is different, and the default is different.
    kind = "stable" if stable else "quicksort"
    if not descending:
        res = np.argsort(x._array, axis=axis, kind=kind)
    else:
        # As NumPy has no native descending sort, we imitate it here. Note that
        # simply flipping the results of np.argsort(x._array, ...) would not
        # respect the relative order like it would in native descending sorts.
        res = np.flip(
            np.argsort(np.flip(x._array, axis=axis), axis=axis, kind=kind),
            axis=axis,
        )
        # Rely on flip()/argsort() to validate axis
        normalised_axis = axis if axis >= 0 else x.ndim + axis
        max_i = x.shape[normalised_axis] - 1
        res = max_i - res
    return Array._new(res)

# Note: the descending keyword argument is new in this function
def sort(
    x: Array, /, *, axis: int = -1, descending: bool = False, stable: bool = True
) -> Array:
    """
    Array API compatible wrapper for :py:func:`np.sort <numpy.sort>`.

    See its docstring for more information.
    """
    if x.dtype not in _real_numeric_dtypes:
        raise TypeError("Only real numeric dtypes are allowed in sort")
    # Note: this keyword argument is different, and the default is different.
    kind = "stable" if stable else "quicksort"
    res = np.sort(x._array, axis=axis, kind=kind)
    if descending:
        res = np.flip(res, axis=axis)
    return Array._new(res)
