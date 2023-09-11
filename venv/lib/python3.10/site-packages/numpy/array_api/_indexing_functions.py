from __future__ import annotations

from ._array_object import Array
from ._dtypes import _integer_dtypes

import numpy as np

def take(x: Array, indices: Array, /, *, axis: Optional[int] = None) -> Array:
    """
    Array API compatible wrapper for :py:func:`np.take <numpy.take>`.

    See its docstring for more information.
    """
    if axis is None and x.ndim != 1:
        raise ValueError("axis must be specified when ndim > 1")
    if indices.dtype not in _integer_dtypes:
        raise TypeError("Only integer dtypes are allowed in indexing")
    if indices.ndim != 1:
        raise ValueError("Only 1-dim indices array is supported")
    return Array._new(np.take(x._array, indices._array, axis=axis))
