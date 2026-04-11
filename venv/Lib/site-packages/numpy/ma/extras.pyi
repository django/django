from _typeshed import Incomplete
from collections.abc import Sequence
from typing import SupportsIndex, TypeAlias, TypeVar, overload

import numpy as np
from numpy import _CastingKind
from numpy._typing import (
    ArrayLike,
    DTypeLike,
    _AnyShape,
    _ArrayLike,
    _DTypeLike,
    _ShapeLike,
)
from numpy.lib._function_base_impl import average
from numpy.lib._index_tricks_impl import AxisConcatenator

from .core import MaskedArray, dot

__all__ = [
    "apply_along_axis",
    "apply_over_axes",
    "atleast_1d",
    "atleast_2d",
    "atleast_3d",
    "average",
    "clump_masked",
    "clump_unmasked",
    "column_stack",
    "compress_cols",
    "compress_nd",
    "compress_rowcols",
    "compress_rows",
    "corrcoef",
    "count_masked",
    "cov",
    "diagflat",
    "dot",
    "dstack",
    "ediff1d",
    "flatnotmasked_contiguous",
    "flatnotmasked_edges",
    "hsplit",
    "hstack",
    "in1d",
    "intersect1d",
    "isin",
    "mask_cols",
    "mask_rowcols",
    "mask_rows",
    "masked_all",
    "masked_all_like",
    "median",
    "mr_",
    "ndenumerate",
    "notmasked_contiguous",
    "notmasked_edges",
    "polyfit",
    "row_stack",
    "setdiff1d",
    "setxor1d",
    "stack",
    "union1d",
    "unique",
    "vander",
    "vstack",
]

_ScalarT = TypeVar("_ScalarT", bound=np.generic)
_ScalarT1 = TypeVar("_ScalarT1", bound=np.generic)
_ScalarT2 = TypeVar("_ScalarT2", bound=np.generic)
_MArrayT = TypeVar("_MArrayT", bound=MaskedArray)

_MArray: TypeAlias = MaskedArray[_AnyShape, np.dtype[_ScalarT]]

###

# keep in sync with `numpy._core.shape_base.atleast_1d`
@overload
def atleast_1d(a0: _ArrayLike[_ScalarT], /) -> _MArray[_ScalarT]: ...
@overload
def atleast_1d(a0: _ArrayLike[_ScalarT1], a1: _ArrayLike[_ScalarT2], /) -> tuple[_MArray[_ScalarT1], _MArray[_ScalarT2]]: ...
@overload
def atleast_1d(
    a0: _ArrayLike[_ScalarT], a1: _ArrayLike[_ScalarT], /, *arys: _ArrayLike[_ScalarT]
) -> tuple[_MArray[_ScalarT], ...]: ...
@overload
def atleast_1d(a0: ArrayLike, /) -> _MArray[Incomplete]: ...
@overload
def atleast_1d(a0: ArrayLike, a1: ArrayLike, /) -> tuple[_MArray[Incomplete], _MArray[Incomplete]]: ...
@overload
def atleast_1d(a0: ArrayLike, a1: ArrayLike, /, *ai: ArrayLike) -> tuple[_MArray[Incomplete], ...]: ...

# keep in sync with `numpy._core.shape_base.atleast_2d`
@overload
def atleast_2d(a0: _ArrayLike[_ScalarT], /) -> _MArray[_ScalarT]: ...
@overload
def atleast_2d(a0: _ArrayLike[_ScalarT1], a1: _ArrayLike[_ScalarT2], /) -> tuple[_MArray[_ScalarT1], _MArray[_ScalarT2]]: ...
@overload
def atleast_2d(
    a0: _ArrayLike[_ScalarT], a1: _ArrayLike[_ScalarT], /, *arys: _ArrayLike[_ScalarT]
) -> tuple[_MArray[_ScalarT], ...]: ...
@overload
def atleast_2d(a0: ArrayLike, /) -> _MArray[Incomplete]: ...
@overload
def atleast_2d(a0: ArrayLike, a1: ArrayLike, /) -> tuple[_MArray[Incomplete], _MArray[Incomplete]]: ...
@overload
def atleast_2d(a0: ArrayLike, a1: ArrayLike, /, *ai: ArrayLike) -> tuple[_MArray[Incomplete], ...]: ...

# keep in sync with `numpy._core.shape_base.atleast_2d`
@overload
def atleast_3d(a0: _ArrayLike[_ScalarT], /) -> _MArray[_ScalarT]: ...
@overload
def atleast_3d(a0: _ArrayLike[_ScalarT1], a1: _ArrayLike[_ScalarT2], /) -> tuple[_MArray[_ScalarT1], _MArray[_ScalarT2]]: ...
@overload
def atleast_3d(
    a0: _ArrayLike[_ScalarT], a1: _ArrayLike[_ScalarT], /, *arys: _ArrayLike[_ScalarT]
) -> tuple[_MArray[_ScalarT], ...]: ...
@overload
def atleast_3d(a0: ArrayLike, /) -> _MArray[Incomplete]: ...
@overload
def atleast_3d(a0: ArrayLike, a1: ArrayLike, /) -> tuple[_MArray[Incomplete], _MArray[Incomplete]]: ...
@overload
def atleast_3d(a0: ArrayLike, a1: ArrayLike, /, *ai: ArrayLike) -> tuple[_MArray[Incomplete], ...]: ...

# keep in sync with `numpy._core.shape_base.vstack`
@overload
def vstack(
    tup: Sequence[_ArrayLike[_ScalarT]],
    *,
    dtype: None = None,
    casting: _CastingKind = "same_kind"
) -> _MArray[_ScalarT]: ...
@overload
def vstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: _DTypeLike[_ScalarT],
    casting: _CastingKind = "same_kind"
) -> _MArray[_ScalarT]: ...
@overload
def vstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind"
) -> _MArray[Incomplete]: ...

row_stack = vstack

# keep in sync with `numpy._core.shape_base.hstack`
@overload
def hstack(
    tup: Sequence[_ArrayLike[_ScalarT]],
    *,
    dtype: None = None,
    casting: _CastingKind = "same_kind"
) -> _MArray[_ScalarT]: ...
@overload
def hstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: _DTypeLike[_ScalarT],
    casting: _CastingKind = "same_kind"
) -> _MArray[_ScalarT]: ...
@overload
def hstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind"
) -> _MArray[Incomplete]: ...

# keep in sync with `numpy._core.shape_base_impl.column_stack`
@overload
def column_stack(tup: Sequence[_ArrayLike[_ScalarT]]) -> _MArray[_ScalarT]: ...
@overload
def column_stack(tup: Sequence[ArrayLike]) -> _MArray[Incomplete]: ...

# keep in sync with `numpy._core.shape_base_impl.dstack`
@overload
def dstack(tup: Sequence[_ArrayLike[_ScalarT]]) -> _MArray[_ScalarT]: ...
@overload
def dstack(tup: Sequence[ArrayLike]) -> _MArray[Incomplete]: ...

# keep in sync with `numpy._core.shape_base.stack`
@overload
def stack(
    arrays: Sequence[_ArrayLike[_ScalarT]],
    axis: SupportsIndex = 0,
    out: None = None,
    *,
    dtype: None = None,
    casting: _CastingKind = "same_kind"
) -> _MArray[_ScalarT]: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex = 0,
    out: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    casting: _CastingKind = "same_kind"
) -> _MArray[_ScalarT]: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex = 0,
    out: None = None,
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind"
) -> _MArray[Incomplete]: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex,
    out: _MArrayT,
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind",
) -> _MArrayT: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex = 0,
    *,
    out: _MArrayT,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind",
) -> _MArrayT: ...

# keep in sync with `numpy._core.shape_base_impl.hsplit`
@overload
def hsplit(ary: _ArrayLike[_ScalarT], indices_or_sections: _ShapeLike) -> list[_MArray[_ScalarT]]: ...
@overload
def hsplit(ary: ArrayLike, indices_or_sections: _ShapeLike) -> list[_MArray[Incomplete]]: ...

# keep in sync with `numpy._core.twodim_base_impl.hsplit`
@overload
def diagflat(v: _ArrayLike[_ScalarT], k: int = 0) -> _MArray[_ScalarT]: ...
@overload
def diagflat(v: ArrayLike, k: int = 0) -> _MArray[Incomplete]: ...

# TODO: everything below

def count_masked(arr, axis=None): ...
def masked_all(shape, dtype=float): ...  # noqa: PYI014
def masked_all_like(arr): ...

def apply_along_axis(func1d, axis, arr, *args, **kwargs): ...
def apply_over_axes(func, a, axes): ...
def median(a, axis=None, out=None, overwrite_input=False, keepdims=False): ...
def compress_nd(x, axis=None): ...
def compress_rowcols(x, axis=None): ...
def compress_rows(a): ...
def compress_cols(a): ...
def mask_rows(a, axis=...): ...
def mask_cols(a, axis=...): ...
def ediff1d(arr, to_end=None, to_begin=None): ...
def unique(ar1, return_index=False, return_inverse=False): ...
def intersect1d(ar1, ar2, assume_unique=False): ...
def setxor1d(ar1, ar2, assume_unique=False): ...
def in1d(ar1, ar2, assume_unique=False, invert=False): ...
def isin(element, test_elements, assume_unique=False, invert=False): ...
def union1d(ar1, ar2): ...
def setdiff1d(ar1, ar2, assume_unique=False): ...
def cov(x, y=None, rowvar=True, bias=False, allow_masked=True, ddof=None): ...
def corrcoef(x, y=None, rowvar=True, allow_masked=True): ...

class MAxisConcatenator(AxisConcatenator):
    __slots__ = ()

    @staticmethod
    def concatenate(arrays: Incomplete, axis: int = 0) -> Incomplete: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
    @classmethod
    def makemat(cls, arr: Incomplete) -> Incomplete: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleVariableOverride]

class mr_class(MAxisConcatenator):
    __slots__ = ()

    def __init__(self) -> None: ...

mr_: mr_class

def ndenumerate(a, compressed=True): ...
def flatnotmasked_edges(a): ...
def notmasked_edges(a, axis=None): ...
def flatnotmasked_contiguous(a): ...
def notmasked_contiguous(a, axis=None): ...
def clump_unmasked(a): ...
def clump_masked(a): ...
def vander(x, n=None): ...
def polyfit(x, y, deg, rcond=None, full=False, w=None, cov=False): ...

#
def mask_rowcols(a: Incomplete, axis: Incomplete | None = None) -> MaskedArray[Incomplete, np.dtype[Incomplete]]: ...
