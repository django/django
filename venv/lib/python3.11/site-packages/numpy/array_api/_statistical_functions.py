from __future__ import annotations

from ._dtypes import (
    _real_floating_dtypes,
    _real_numeric_dtypes,
    _numeric_dtypes,
)
from ._array_object import Array
from ._dtypes import float32, float64, complex64, complex128

from typing import TYPE_CHECKING, Optional, Tuple, Union

if TYPE_CHECKING:
    from ._typing import Dtype

import numpy as np


def max(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    keepdims: bool = False,
) -> Array:
    if x.dtype not in _real_numeric_dtypes:
        raise TypeError("Only real numeric dtypes are allowed in max")
    return Array._new(np.max(x._array, axis=axis, keepdims=keepdims))


def mean(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    keepdims: bool = False,
) -> Array:
    if x.dtype not in _real_floating_dtypes:
        raise TypeError("Only real floating-point dtypes are allowed in mean")
    return Array._new(np.mean(x._array, axis=axis, keepdims=keepdims))


def min(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    keepdims: bool = False,
) -> Array:
    if x.dtype not in _real_numeric_dtypes:
        raise TypeError("Only real numeric dtypes are allowed in min")
    return Array._new(np.min(x._array, axis=axis, keepdims=keepdims))


def prod(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    dtype: Optional[Dtype] = None,
    keepdims: bool = False,
) -> Array:
    if x.dtype not in _numeric_dtypes:
        raise TypeError("Only numeric dtypes are allowed in prod")
    # Note: sum() and prod() always upcast for dtype=None. `np.prod` does that
    # for integers, but not for float32 or complex64, so we need to
    # special-case it here
    if dtype is None:
        if x.dtype == float32:
            dtype = float64
        elif x.dtype == complex64:
            dtype = complex128
    return Array._new(np.prod(x._array, dtype=dtype, axis=axis, keepdims=keepdims))


def std(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    correction: Union[int, float] = 0.0,
    keepdims: bool = False,
) -> Array:
    # Note: the keyword argument correction is different here
    if x.dtype not in _real_floating_dtypes:
        raise TypeError("Only real floating-point dtypes are allowed in std")
    return Array._new(np.std(x._array, axis=axis, ddof=correction, keepdims=keepdims))


def sum(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    dtype: Optional[Dtype] = None,
    keepdims: bool = False,
) -> Array:
    if x.dtype not in _numeric_dtypes:
        raise TypeError("Only numeric dtypes are allowed in sum")
    # Note: sum() and prod() always upcast for dtype=None. `np.sum` does that
    # for integers, but not for float32 or complex64, so we need to
    # special-case it here
    if dtype is None:
        if x.dtype == float32:
            dtype = float64
        elif x.dtype == complex64:
            dtype = complex128
    return Array._new(np.sum(x._array, axis=axis, dtype=dtype, keepdims=keepdims))


def var(
    x: Array,
    /,
    *,
    axis: Optional[Union[int, Tuple[int, ...]]] = None,
    correction: Union[int, float] = 0.0,
    keepdims: bool = False,
) -> Array:
    # Note: the keyword argument correction is different here
    if x.dtype not in _real_floating_dtypes:
        raise TypeError("Only real floating-point dtypes are allowed in var")
    return Array._new(np.var(x._array, axis=axis, ddof=correction, keepdims=keepdims))
