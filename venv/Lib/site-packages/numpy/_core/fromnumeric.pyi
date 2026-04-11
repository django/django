# ruff: noqa: ANN401
from _typeshed import Incomplete
from collections.abc import Sequence
from typing import (
    Any,
    Literal,
    Never,
    Protocol,
    SupportsIndex,
    TypeAlias,
    TypedDict,
    TypeVar,
    Unpack,
    overload,
    type_check_only,
)

import numpy as np
from numpy import (
    _AnyShapeT,
    _CastingKind,
    _ModeKind,
    _OrderACF,
    _OrderKACF,
    _PartitionKind,
    _SortKind,
    _SortSide,
    complexfloating,
    float16,
    floating,
    generic,
    int64,
    int_,
    intp,
    object_,
    timedelta64,
    uint64,
)
from numpy._globals import _NoValueType
from numpy._typing import (
    ArrayLike,
    DTypeLike,
    NDArray,
    _AnyShape,
    _ArrayLike,
    _ArrayLikeBool_co,
    _ArrayLikeComplex_co,
    _ArrayLikeFloat_co,
    _ArrayLikeInt,
    _ArrayLikeInt_co,
    _ArrayLikeObject_co,
    _ArrayLikeUInt_co,
    _BoolLike_co,
    _ComplexLike_co,
    _DTypeLike,
    _IntLike_co,
    _NestedSequence,
    _NumberLike_co,
    _ScalarLike_co,
    _ShapeLike,
)

__all__ = [
    "all",
    "amax",
    "amin",
    "any",
    "argmax",
    "argmin",
    "argpartition",
    "argsort",
    "around",
    "choose",
    "clip",
    "compress",
    "cumprod",
    "cumsum",
    "cumulative_prod",
    "cumulative_sum",
    "diagonal",
    "mean",
    "max",
    "min",
    "matrix_transpose",
    "ndim",
    "nonzero",
    "partition",
    "prod",
    "ptp",
    "put",
    "ravel",
    "repeat",
    "reshape",
    "resize",
    "round",
    "searchsorted",
    "shape",
    "size",
    "sort",
    "squeeze",
    "std",
    "sum",
    "swapaxes",
    "take",
    "trace",
    "transpose",
    "var",
]

_ScalarT = TypeVar("_ScalarT", bound=generic)
_NumberOrObjectT = TypeVar("_NumberOrObjectT", bound=np.number | np.object_)
_ArrayT = TypeVar("_ArrayT", bound=np.ndarray[Any, Any])
_ShapeT = TypeVar("_ShapeT", bound=tuple[int, ...])
_ShapeT_co = TypeVar("_ShapeT_co", bound=tuple[int, ...], covariant=True)
_BoolOrIntArrayT = TypeVar("_BoolOrIntArrayT", bound=NDArray[np.integer | np.bool])

@type_check_only
class _SupportsShape(Protocol[_ShapeT_co]):
    # NOTE: it matters that `self` is positional only
    @property
    def shape(self, /) -> _ShapeT_co: ...

@type_check_only
class _UFuncKwargs(TypedDict, total=False):
    where: _ArrayLikeBool_co | None
    order: _OrderKACF
    subok: bool
    signature: str | tuple[str | None, ...]
    casting: _CastingKind

# a "sequence" that isn't a string, bytes, bytearray, or memoryview
_T = TypeVar("_T")
_PyArray: TypeAlias = list[_T] | tuple[_T, ...]
# `int` also covers `bool`
_PyScalar: TypeAlias = complex | bytes | str

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def take(
    a: _ArrayLike[_ScalarT],
    indices: _IntLike_co,
    axis: None = None,
    out: None = None,
    mode: _ModeKind = "raise",
) -> _ScalarT: ...
@overload
def take(
    a: ArrayLike,
    indices: _IntLike_co,
    axis: SupportsIndex | None = None,
    out: None = None,
    mode: _ModeKind = "raise",
) -> Any: ...
@overload
def take(
    a: _ArrayLike[_ScalarT],
    indices: _ArrayLikeInt_co,
    axis: SupportsIndex | None = None,
    out: None = None,
    mode: _ModeKind = "raise",
) -> NDArray[_ScalarT]: ...
@overload
def take(
    a: ArrayLike,
    indices: _ArrayLikeInt_co,
    axis: SupportsIndex | None = None,
    out: None = None,
    mode: _ModeKind = "raise",
) -> NDArray[Any]: ...
@overload
def take(
    a: ArrayLike,
    indices: _ArrayLikeInt_co,
    axis: SupportsIndex | None,
    out: _ArrayT,
    mode: _ModeKind = "raise",
) -> _ArrayT: ...
@overload
def take(
    a: ArrayLike,
    indices: _ArrayLikeInt_co,
    axis: SupportsIndex | None = None,
    *,
    out: _ArrayT,
    mode: _ModeKind = "raise",
) -> _ArrayT: ...

@overload
def reshape(  # shape: index
    a: _ArrayLike[_ScalarT],
    /,
    shape: SupportsIndex,
    order: _OrderACF = "C",
    *,
    copy: bool | None = None,
) -> np.ndarray[tuple[int], np.dtype[_ScalarT]]: ...
@overload
def reshape(  # shape: (int, ...) @ _AnyShapeT
    a: _ArrayLike[_ScalarT],
    /,
    shape: _AnyShapeT,
    order: _OrderACF = "C",
    *,
    copy: bool | None = None,
) -> np.ndarray[_AnyShapeT, np.dtype[_ScalarT]]: ...
@overload  # shape: Sequence[index]
def reshape(
    a: _ArrayLike[_ScalarT],
    /,
    shape: Sequence[SupportsIndex],
    order: _OrderACF = "C",
    *,
    copy: bool | None = None,
) -> NDArray[_ScalarT]: ...
@overload  # shape: index
def reshape(
    a: ArrayLike,
    /,
    shape: SupportsIndex,
    order: _OrderACF = "C",
    *,
    copy: bool | None = None,
) -> np.ndarray[tuple[int], np.dtype]: ...
@overload
def reshape(  # shape: (int, ...) @ _AnyShapeT
    a: ArrayLike,
    /,
    shape: _AnyShapeT,
    order: _OrderACF = "C",
    *,
    copy: bool | None = None,
) -> np.ndarray[_AnyShapeT, np.dtype]: ...
@overload  # shape: Sequence[index]
def reshape(
    a: ArrayLike,
    /,
    shape: Sequence[SupportsIndex],
    order: _OrderACF = "C",
    *,
    copy: bool | None = None,
) -> NDArray[Any]: ...

@overload
def choose(
    a: _IntLike_co,
    choices: ArrayLike,
    out: None = None,
    mode: _ModeKind = "raise",
) -> Any: ...
@overload
def choose(
    a: _ArrayLikeInt_co,
    choices: _ArrayLike[_ScalarT],
    out: None = None,
    mode: _ModeKind = "raise",
) -> NDArray[_ScalarT]: ...
@overload
def choose(
    a: _ArrayLikeInt_co,
    choices: ArrayLike,
    out: None = None,
    mode: _ModeKind = "raise",
) -> NDArray[Any]: ...
@overload
def choose(
    a: _ArrayLikeInt_co,
    choices: ArrayLike,
    out: _ArrayT,
    mode: _ModeKind = "raise",
) -> _ArrayT: ...

# keep in sync with `ma.core.repeat`
@overload
def repeat(
    a: _ArrayLike[_ScalarT],
    repeats: _ArrayLikeInt_co,
    axis: None = None,
) -> np.ndarray[tuple[int], np.dtype[_ScalarT]]: ...
@overload
def repeat(
    a: _ArrayLike[_ScalarT],
    repeats: _ArrayLikeInt_co,
    axis: SupportsIndex,
) -> NDArray[_ScalarT]: ...
@overload
def repeat(
    a: ArrayLike,
    repeats: _ArrayLikeInt_co,
    axis: None = None,
) -> np.ndarray[tuple[int], np.dtype[Any]]: ...
@overload
def repeat(
    a: ArrayLike,
    repeats: _ArrayLikeInt_co,
    axis: SupportsIndex,
) -> NDArray[Any]: ...

#
def put(
    a: NDArray[Any],
    ind: _ArrayLikeInt_co,
    v: ArrayLike,
    mode: _ModeKind = "raise",
) -> None: ...

# keep in sync with `ndarray.swapaxes` and `ma.core.swapaxes`
@overload
def swapaxes(a: _ArrayT, axis1: SupportsIndex, axis2: SupportsIndex) -> _ArrayT: ...
@overload
def swapaxes(a: _ArrayLike[_ScalarT], axis1: SupportsIndex, axis2: SupportsIndex) -> NDArray[_ScalarT]: ...
@overload
def swapaxes(a: ArrayLike, axis1: SupportsIndex, axis2: SupportsIndex) -> NDArray[Any]: ...

@overload
def transpose(
    a: _ArrayLike[_ScalarT],
    axes: _ShapeLike | None = None,
) -> NDArray[_ScalarT]: ...
@overload
def transpose(
    a: ArrayLike,
    axes: _ShapeLike | None = None,
) -> NDArray[Any]: ...

@overload
def matrix_transpose(x: _ArrayLike[_ScalarT], /) -> NDArray[_ScalarT]: ...
@overload
def matrix_transpose(x: ArrayLike, /) -> NDArray[Any]: ...

#
@overload
def partition(
    a: _ArrayLike[_ScalarT],
    kth: _ArrayLikeInt,
    axis: SupportsIndex | None = -1,
    kind: _PartitionKind = "introselect",
    order: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def partition(
    a: _ArrayLike[np.void],
    kth: _ArrayLikeInt,
    axis: SupportsIndex | None = -1,
    kind: _PartitionKind = "introselect",
    order: str | Sequence[str] | None = None,
) -> NDArray[np.void]: ...
@overload
def partition(
    a: ArrayLike,
    kth: _ArrayLikeInt,
    axis: SupportsIndex | None = -1,
    kind: _PartitionKind = "introselect",
    order: str | Sequence[str] | None = None,
) -> NDArray[Any]: ...

#
def argpartition(
    a: ArrayLike,
    kth: _ArrayLikeInt,
    axis: SupportsIndex | None = -1,
    kind: _PartitionKind = "introselect",
    order: str | Sequence[str] | None = None,
) -> NDArray[intp]: ...

#
@overload
def sort(
    a: _ArrayLike[_ScalarT],
    axis: SupportsIndex | None = -1,
    kind: _SortKind | None = None,
    order: str | Sequence[str] | None = None,
    *,
    stable: bool | None = None,
) -> NDArray[_ScalarT]: ...
@overload
def sort(
    a: ArrayLike,
    axis: SupportsIndex | None = -1,
    kind: _SortKind | None = None,
    order: str | Sequence[str] | None = None,
    *,
    stable: bool | None = None,
) -> NDArray[Any]: ...

def argsort(
    a: ArrayLike,
    axis: SupportsIndex | None = -1,
    kind: _SortKind | None = None,
    order: str | Sequence[str] | None = None,
    *,
    stable: bool | None = None,
) -> NDArray[intp]: ...

@overload
def argmax(
    a: ArrayLike,
    axis: None = None,
    out: None = None,
    *,
    keepdims: Literal[False] | _NoValueType = ...,
) -> intp: ...
@overload
def argmax(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    out: None = None,
    *,
    keepdims: bool | _NoValueType = ...,
) -> Any: ...
@overload
def argmax(
    a: ArrayLike,
    axis: SupportsIndex | None,
    out: _BoolOrIntArrayT,
    *,
    keepdims: bool | _NoValueType = ...,
) -> _BoolOrIntArrayT: ...
@overload
def argmax(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    *,
    out: _BoolOrIntArrayT,
    keepdims: bool | _NoValueType = ...,
) -> _BoolOrIntArrayT: ...

@overload
def argmin(
    a: ArrayLike,
    axis: None = None,
    out: None = None,
    *,
    keepdims: Literal[False] | _NoValueType = ...,
) -> intp: ...
@overload
def argmin(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    out: None = None,
    *,
    keepdims: bool | _NoValueType = ...,
) -> Any: ...
@overload
def argmin(
    a: ArrayLike,
    axis: SupportsIndex | None,
    out: _BoolOrIntArrayT,
    *,
    keepdims: bool | _NoValueType = ...,
) -> _BoolOrIntArrayT: ...
@overload
def argmin(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    *,
    out: _BoolOrIntArrayT,
    keepdims: bool | _NoValueType = ...,
) -> _BoolOrIntArrayT: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def searchsorted(
    a: ArrayLike,
    v: _ScalarLike_co,
    side: _SortSide = "left",
    sorter: _ArrayLikeInt_co | None = None,  # 1D int array
) -> intp: ...
@overload
def searchsorted(
    a: ArrayLike,
    v: ArrayLike,
    side: _SortSide = "left",
    sorter: _ArrayLikeInt_co | None = None,  # 1D int array
) -> NDArray[intp]: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def resize(a: _ArrayLike[_ScalarT], new_shape: SupportsIndex | tuple[SupportsIndex]) -> np.ndarray[tuple[int], np.dtype[_ScalarT]]: ...
@overload
def resize(a: _ArrayLike[_ScalarT], new_shape: _AnyShapeT) -> np.ndarray[_AnyShapeT, np.dtype[_ScalarT]]: ...
@overload
def resize(a: _ArrayLike[_ScalarT], new_shape: _ShapeLike) -> NDArray[_ScalarT]: ...
@overload
def resize(a: ArrayLike, new_shape: SupportsIndex | tuple[SupportsIndex]) -> np.ndarray[tuple[int], np.dtype]: ...
@overload
def resize(a: ArrayLike, new_shape: _AnyShapeT) -> np.ndarray[_AnyShapeT, np.dtype]: ...
@overload
def resize(a: ArrayLike, new_shape: _ShapeLike) -> NDArray[Any]: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def squeeze(
    a: _ScalarT,
    axis: _ShapeLike | None = None,
) -> _ScalarT: ...
@overload
def squeeze(
    a: _ArrayLike[_ScalarT],
    axis: _ShapeLike | None = None,
) -> NDArray[_ScalarT]: ...
@overload
def squeeze(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
) -> NDArray[Any]: ...

# keep in sync with `ma.core.diagonal`
@overload
def diagonal(
    a: _ArrayLike[_ScalarT],
    offset: SupportsIndex = 0,
    axis1: SupportsIndex = 0,
    axis2: SupportsIndex = 1,  # >= 2D array
) -> NDArray[_ScalarT]: ...
@overload
def diagonal(
    a: ArrayLike,
    offset: SupportsIndex = 0,
    axis1: SupportsIndex = 0,
    axis2: SupportsIndex = 1,  # >= 2D array
) -> NDArray[Any]: ...

# keep in sync with `ma.core.trace`
@overload
def trace(
    a: ArrayLike,  # >= 2D array
    offset: SupportsIndex = 0,
    axis1: SupportsIndex = 0,
    axis2: SupportsIndex = 1,
    dtype: DTypeLike | None = None,
    out: None = None,
) -> Any: ...
@overload
def trace(
    a: ArrayLike,  # >= 2D array
    offset: SupportsIndex,
    axis1: SupportsIndex,
    axis2: SupportsIndex,
    dtype: DTypeLike | None,
    out: _ArrayT,
) -> _ArrayT: ...
@overload
def trace(
    a: ArrayLike,  # >= 2D array
    offset: SupportsIndex = 0,
    axis1: SupportsIndex = 0,
    axis2: SupportsIndex = 1,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
) -> _ArrayT: ...

_Array1D: TypeAlias = np.ndarray[tuple[int], np.dtype[_ScalarT]]

@overload
def ravel(a: _ArrayLike[_ScalarT], order: _OrderKACF = "C") -> _Array1D[_ScalarT]: ...
@overload
def ravel(a: bytes | _NestedSequence[bytes], order: _OrderKACF = "C") -> _Array1D[np.bytes_]: ...
@overload
def ravel(a: str | _NestedSequence[str], order: _OrderKACF = "C") -> _Array1D[np.str_]: ...
@overload
def ravel(a: bool | _NestedSequence[bool], order: _OrderKACF = "C") -> _Array1D[np.bool]: ...
@overload
def ravel(a: int | _NestedSequence[int], order: _OrderKACF = "C") -> _Array1D[np.int_ | Any]: ...
@overload
def ravel(a: float | _NestedSequence[float], order: _OrderKACF = "C") -> _Array1D[np.float64 | Any]: ...
@overload
def ravel(a: complex | _NestedSequence[complex], order: _OrderKACF = "C") -> _Array1D[np.complex128 | Any]: ...
@overload
def ravel(a: ArrayLike, order: _OrderKACF = "C") -> np.ndarray[tuple[int], np.dtype]: ...

def nonzero(a: _ArrayLike[Any]) -> tuple[np.ndarray[tuple[int], np.dtype[intp]], ...]: ...

# this prevents `Any` from being returned with Pyright
@overload
def shape(a: _SupportsShape[Never]) -> _AnyShape: ...
@overload
def shape(a: _SupportsShape[_ShapeT]) -> _ShapeT: ...
@overload
def shape(a: _PyScalar) -> tuple[()]: ...
# `collections.abc.Sequence` can't be used hesre, since `bytes` and `str` are
# subtypes of it, which would make the return types incompatible.
@overload
def shape(a: _PyArray[_PyScalar]) -> tuple[int]: ...
@overload
def shape(a: _PyArray[_PyArray[_PyScalar]]) -> tuple[int, int]: ...
# this overload will be skipped by typecheckers that don't support PEP 688
@overload
def shape(a: memoryview | bytearray) -> tuple[int]: ...
@overload
def shape(a: ArrayLike) -> _AnyShape: ...

@overload
def compress(
    condition: _ArrayLikeBool_co,  # 1D bool array
    a: _ArrayLike[_ScalarT],
    axis: SupportsIndex | None = None,
    out: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def compress(
    condition: _ArrayLikeBool_co,  # 1D bool array
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    out: None = None,
) -> NDArray[Any]: ...
@overload
def compress(
    condition: _ArrayLikeBool_co,  # 1D bool array
    a: ArrayLike,
    axis: SupportsIndex | None,
    out: _ArrayT,
) -> _ArrayT: ...
@overload
def compress(
    condition: _ArrayLikeBool_co,  # 1D bool array
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    *,
    out: _ArrayT,
) -> _ArrayT: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def clip(
    a: _ScalarT,
    a_min: ArrayLike | _NoValueType | None = ...,
    a_max: ArrayLike | _NoValueType | None = ...,
    out: None = None,
    *,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> _ScalarT: ...
@overload
def clip(
    a: _ScalarLike_co,
    a_min: ArrayLike | _NoValueType | None = ...,
    a_max: ArrayLike | _NoValueType | None = ...,
    out: None = None,
    *,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> Any: ...
@overload
def clip(
    a: _ArrayLike[_ScalarT],
    a_min: ArrayLike | _NoValueType | None = ...,
    a_max: ArrayLike | _NoValueType | None = ...,
    out: None = None,
    *,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> NDArray[_ScalarT]: ...
@overload
def clip(
    a: ArrayLike,
    a_min: ArrayLike | _NoValueType | None = ...,
    a_max: ArrayLike | _NoValueType | None = ...,
    out: None = None,
    *,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> NDArray[Any]: ...
@overload
def clip(
    a: ArrayLike,
    a_min: ArrayLike | None,
    a_max: ArrayLike | None,
    out: _ArrayT,
    *,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: DTypeLike | None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> _ArrayT: ...
@overload
def clip(
    a: ArrayLike,
    a_min: ArrayLike | _NoValueType | None = ...,
    a_max: ArrayLike | _NoValueType | None = ...,
    *,
    out: _ArrayT,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: DTypeLike | None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> _ArrayT: ...
@overload
def clip(
    a: ArrayLike,
    a_min: ArrayLike | _NoValueType | None = ...,
    a_max: ArrayLike | _NoValueType | None = ...,
    out: None = None,
    *,
    min: ArrayLike | _NoValueType | None = ...,
    max: ArrayLike | _NoValueType | None = ...,
    dtype: DTypeLike | None = None,
    **kwargs: Unpack[_UFuncKwargs],
) -> Any: ...

@overload
def sum(
    a: _ArrayLike[_ScalarT],
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def sum(
    a: _ArrayLike[_ScalarT],
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT | NDArray[_ScalarT]: ...
@overload
def sum(
    a: ArrayLike,
    axis: None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def sum(
    a: ArrayLike,
    axis: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def sum(
    a: ArrayLike,
    axis: _ShapeLike | None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT | NDArray[_ScalarT]: ...
@overload
def sum(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT | NDArray[_ScalarT]: ...
@overload
def sum(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Any: ...
@overload
def sum(
    a: ArrayLike,
    axis: _ShapeLike | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def sum(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...

# keep in sync with `any`
@overload
def all(
    a: ArrayLike | None,
    axis: None = None,
    out: None = None,
    keepdims: Literal[False, 0] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> np.bool: ...
@overload
def all(
    a: ArrayLike | None,
    axis: int | tuple[int, ...] | None = None,
    out: None = None,
    keepdims: _BoolLike_co | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Incomplete: ...
@overload
def all(
    a: ArrayLike | None,
    axis: int | tuple[int, ...] | None,
    out: _ArrayT,
    keepdims: _BoolLike_co | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def all(
    a: ArrayLike | None,
    axis: int | tuple[int, ...] | None = None,
    *,
    out: _ArrayT,
    keepdims: _BoolLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...

# keep in sync with `all`
@overload
def any(
    a: ArrayLike | None,
    axis: None = None,
    out: None = None,
    keepdims: Literal[False, 0] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> np.bool: ...
@overload
def any(
    a: ArrayLike | None,
    axis: int | tuple[int, ...] | None = None,
    out: None = None,
    keepdims: _BoolLike_co | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Incomplete: ...
@overload
def any(
    a: ArrayLike | None,
    axis: int | tuple[int, ...] | None,
    out: _ArrayT,
    keepdims: _BoolLike_co | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def any(
    a: ArrayLike | None,
    axis: int | tuple[int, ...] | None = None,
    *,
    out: _ArrayT,
    keepdims: _BoolLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...

#
@overload
def cumsum(
    a: _ArrayLike[_ScalarT],
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def cumsum(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[Any]: ...
@overload
def cumsum(
    a: ArrayLike,
    axis: SupportsIndex | None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def cumsum(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def cumsum(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
) -> NDArray[Any]: ...
@overload
def cumsum(
    a: ArrayLike,
    axis: SupportsIndex | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
) -> _ArrayT: ...
@overload
def cumsum(
    a: ArrayLike,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
) -> _ArrayT: ...

@overload
def cumulative_sum(
    x: _ArrayLike[_ScalarT],
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[_ScalarT]: ...
@overload
def cumulative_sum(
    x: ArrayLike,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[Any]: ...
@overload
def cumulative_sum(
    x: ArrayLike,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    include_initial: bool = False,
) -> NDArray[_ScalarT]: ...
@overload
def cumulative_sum(
    x: ArrayLike,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[Any]: ...
@overload
def cumulative_sum(
    x: ArrayLike,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    out: _ArrayT,
    include_initial: bool = False,
) -> _ArrayT: ...

@overload
def ptp(
    a: _ArrayLike[_ScalarT],
    axis: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def ptp(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
) -> Any: ...
@overload
def ptp(
    a: ArrayLike,
    axis: _ShapeLike | None,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def ptp(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    *,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
) -> _ArrayT: ...

@overload
def amax(
    a: _ArrayLike[_ScalarT],
    axis: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def amax(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Any: ...
@overload
def amax(
    a: ArrayLike,
    axis: _ShapeLike | None,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def amax(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    *,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...

@overload
def amin(
    a: _ArrayLike[_ScalarT],
    axis: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def amin(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Any: ...
@overload
def amin(
    a: ArrayLike,
    axis: _ShapeLike | None,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def amin(
    a: ArrayLike,
    axis: _ShapeLike | None = None,
    *,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...

# TODO: `np.prod()``: For object arrays `initial` does not necessarily
# have to be a numerical scalar.
# The only requirement is that it is compatible
# with the `.__mul__()` method(s) of the passed array's elements.
# Note that the same situation holds for all wrappers around
# `np.ufunc.reduce`, e.g. `np.sum()` (`.__add__()`).
# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def prod(
    a: _ArrayLikeBool_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> int_: ...
@overload
def prod(
    a: _ArrayLikeUInt_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> uint64: ...
@overload
def prod(
    a: _ArrayLikeInt_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> int64: ...
@overload
def prod(
    a: _ArrayLikeFloat_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> floating: ...
@overload
def prod(
    a: _ArrayLikeComplex_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> complexfloating: ...
@overload
def prod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Any: ...
@overload
def prod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def prod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def prod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Any: ...
@overload
def prod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def prod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    initial: _NumberLike_co | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def cumprod(
    a: _ArrayLikeBool_co,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[int_]: ...
@overload
def cumprod(
    a: _ArrayLikeUInt_co,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[uint64]: ...
@overload
def cumprod(
    a: _ArrayLikeInt_co,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[int64]: ...
@overload
def cumprod(
    a: _ArrayLikeFloat_co,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[floating]: ...
@overload
def cumprod(
    a: _ArrayLikeComplex_co,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[complexfloating]: ...
@overload
def cumprod(
    a: _ArrayLikeObject_co,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
) -> NDArray[object_]: ...
@overload
def cumprod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: SupportsIndex | None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def cumprod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: SupportsIndex | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
) -> NDArray[_ScalarT]: ...
@overload
def cumprod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
) -> NDArray[Any]: ...
@overload
def cumprod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: SupportsIndex | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
) -> _ArrayT: ...
@overload
def cumprod(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
) -> _ArrayT: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def cumulative_prod(
    x: _ArrayLikeBool_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[int_]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeUInt_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[uint64]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeInt_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[int64]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeFloat_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[floating]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeComplex_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[complexfloating]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeObject_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[object_]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    include_initial: bool = False,
) -> NDArray[_ScalarT]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    include_initial: bool = False,
) -> NDArray[Any]: ...
@overload
def cumulative_prod(
    x: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    /,
    *,
    axis: SupportsIndex | None = None,
    dtype: DTypeLike | None = None,
    out: _ArrayT,
    include_initial: bool = False,
) -> _ArrayT: ...

def ndim(a: ArrayLike) -> int: ...

def size(a: ArrayLike, axis: int | tuple[int, ...] | None = None) -> int: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def around(
    a: _BoolLike_co,
    decimals: SupportsIndex = 0,
    out: None = None,
) -> float16: ...
@overload
def around(
    a: _NumberOrObjectT,
    decimals: SupportsIndex = 0,
    out: None = None,
) -> _NumberOrObjectT: ...
@overload
def around(
    a: _ComplexLike_co | object_,
    decimals: SupportsIndex = 0,
    out: None = None,
) -> Any: ...
@overload
def around(
    a: _ArrayLikeBool_co,
    decimals: SupportsIndex = 0,
    out: None = None,
) -> NDArray[float16]: ...
@overload
def around(
    a: _ArrayLike[_NumberOrObjectT],
    decimals: SupportsIndex = 0,
    out: None = None,
) -> NDArray[_NumberOrObjectT]: ...
@overload
def around(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    decimals: SupportsIndex = 0,
    out: None = None,
) -> NDArray[Any]: ...
@overload
def around(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    decimals: SupportsIndex,
    out: _ArrayT,
) -> _ArrayT: ...
@overload
def around(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    decimals: SupportsIndex = 0,
    *,
    out: _ArrayT,
) -> _ArrayT: ...

# TODO: Fix overlapping overloads: https://github.com/numpy/numpy/issues/27032
@overload
def mean(
    a: _ArrayLikeFloat_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> floating: ...
@overload
def mean(
    a: _ArrayLikeComplex_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> complexfloating: ...
@overload
def mean(
    a: _ArrayLike[np.timedelta64],
    axis: None = None,
    dtype: None = None,
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> timedelta64: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
    keepdims: bool | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: Literal[False] | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None,
    dtype: _DTypeLike[_ScalarT],
    out: None,
    keepdims: Literal[True, 1],
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> NDArray[_ScalarT]: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    *,
    keepdims: bool | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT | NDArray[_ScalarT]: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> _ScalarT | NDArray[_ScalarT]: ...
@overload
def mean(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
) -> Incomplete: ...

@overload
def std(
    a: _ArrayLikeComplex_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    ddof: float = 0,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> floating: ...
@overload
def std(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: None = None,
    out: None = None,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> Any: ...
@overload
def std(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    ddof: float = 0,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def std(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    ddof: float = 0,
    keepdims: Literal[False] | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def std(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> Any: ...
@overload
def std(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def std(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ArrayT: ...

@overload
def var(
    a: _ArrayLikeComplex_co,
    axis: None = None,
    dtype: None = None,
    out: None = None,
    ddof: float = 0,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> floating: ...
@overload
def var(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: None = None,
    out: None = None,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> Any: ...
@overload
def var(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    ddof: float = 0,
    keepdims: Literal[False] | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def var(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    out: None = None,
    ddof: float = 0,
    keepdims: Literal[False] | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ScalarT: ...
@overload
def var(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    out: None = None,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> Any: ...
@overload
def var(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None,
    dtype: DTypeLike | None,
    out: _ArrayT,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    *,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ArrayT: ...
@overload
def var(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: _ShapeLike | None = None,
    dtype: DTypeLike | None = None,
    *,
    out: _ArrayT,
    ddof: float = 0,
    keepdims: bool | _NoValueType = ...,
    where: _ArrayLikeBool_co | _NoValueType = ...,
    mean: _ArrayLikeComplex_co | _ArrayLikeObject_co | _NoValueType = ...,
    correction: float | _NoValueType = ...,
) -> _ArrayT: ...

max = amax
min = amin
round = around
