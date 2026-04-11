from _typeshed import ConvertibleToInt, Incomplete
from collections.abc import Callable, Iterable, Sequence
from typing import (
    Any,
    Concatenate,
    Literal as L,
    Never,
    ParamSpec,
    Protocol,
    SupportsIndex,
    SupportsInt,
    TypeAlias,
    overload,
    type_check_only,
)
from typing_extensions import TypeIs, TypeVar

import numpy as np
from numpy import _OrderKACF
from numpy._core.multiarray import bincount
from numpy._globals import _NoValueType
from numpy._typing import (
    ArrayLike,
    DTypeLike,
    NDArray,
    _ArrayLike,
    _ArrayLikeBool_co,
    _ArrayLikeComplex_co,
    _ArrayLikeFloat_co,
    _ArrayLikeInt_co,
    _ArrayLikeNumber_co,
    _ArrayLikeObject_co,
    _ComplexLike_co,
    _DTypeLike,
    _FloatLike_co,
    _NestedSequence as _SeqND,
    _NumberLike_co,
    _ScalarLike_co,
    _ShapeLike,
    _SupportsArray,
)

__all__ = [
    "select",
    "piecewise",
    "trim_zeros",
    "copy",
    "iterable",
    "percentile",
    "diff",
    "gradient",
    "angle",
    "unwrap",
    "sort_complex",
    "flip",
    "rot90",
    "extract",
    "place",
    "vectorize",
    "asarray_chkfinite",
    "average",
    "bincount",
    "digitize",
    "cov",
    "corrcoef",
    "median",
    "sinc",
    "hamming",
    "hanning",
    "bartlett",
    "blackman",
    "kaiser",
    "trapezoid",
    "i0",
    "meshgrid",
    "delete",
    "insert",
    "append",
    "interp",
    "quantile",
]

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
# The `{}ss` suffix refers to the PEP 695 (Python 3.12) `ParamSpec` syntax, `**P`.
_Tss = ParamSpec("_Tss")

_ScalarT = TypeVar("_ScalarT", bound=np.generic)
_ScalarT1 = TypeVar("_ScalarT1", bound=np.generic)
_ScalarT2 = TypeVar("_ScalarT2", bound=np.generic)
_FloatingT = TypeVar("_FloatingT", bound=np.floating)
_InexactT = TypeVar("_InexactT", bound=np.inexact)
_InexactTimeT = TypeVar("_InexactTimeT", bound=np.inexact | np.timedelta64)
_InexactDateTimeT = TypeVar("_InexactDateTimeT", bound=np.inexact | np.timedelta64 | np.datetime64)
_ScalarNumericT = TypeVar("_ScalarNumericT", bound=np.inexact | np.timedelta64 | np.object_)
_AnyDoubleT = TypeVar("_AnyDoubleT", bound=np.float64 | np.longdouble | np.complex128 | np.clongdouble)

_ArrayT = TypeVar("_ArrayT", bound=np.ndarray)
_ArrayFloatingT = TypeVar("_ArrayFloatingT", bound=NDArray[np.floating])
_ArrayFloatObjT = TypeVar("_ArrayFloatObjT", bound=NDArray[np.floating | np.object_])
_ArrayComplexT = TypeVar("_ArrayComplexT", bound=NDArray[np.complexfloating])
_ArrayInexactT = TypeVar("_ArrayInexactT", bound=NDArray[np.inexact])
_ArrayNumericT = TypeVar("_ArrayNumericT", bound=NDArray[np.inexact | np.timedelta64 | np.object_])

_ArrayLike1D: TypeAlias = _SupportsArray[np.dtype[_ScalarT]] | Sequence[_ScalarT]

_ShapeT = TypeVar("_ShapeT", bound=tuple[int, ...])

_integer_co: TypeAlias = np.integer | np.bool
_float64_co: TypeAlias = np.float64 | _integer_co
_floating_co: TypeAlias = np.floating | _integer_co

# non-trivial scalar-types that will become `complex128` in `sort_complex()`,
# i.e. all numeric scalar types except for `[u]int{8,16} | longdouble`
_SortsToComplex128: TypeAlias = (
    np.bool
    | np.int32
    | np.uint32
    | np.int64
    | np.uint64
    | np.float16
    | np.float32
    | np.float64
    | np.timedelta64
    | np.object_
)

_Array: TypeAlias = np.ndarray[_ShapeT, np.dtype[_ScalarT]]
_Array0D: TypeAlias = np.ndarray[tuple[()], np.dtype[_ScalarT]]
_Array1D: TypeAlias = np.ndarray[tuple[int], np.dtype[_ScalarT]]
_Array2D: TypeAlias = np.ndarray[tuple[int, int], np.dtype[_ScalarT]]
_Array3D: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[_ScalarT]]
_ArrayMax2D: TypeAlias = np.ndarray[tuple[int] | tuple[int, int], np.dtype[_ScalarT]]
# workaround for mypy and pyright not following the typing spec for overloads
_ArrayNoD: TypeAlias = np.ndarray[tuple[Never, Never, Never, Never], np.dtype[_ScalarT]]

_Seq1D: TypeAlias = Sequence[_T]
_Seq2D: TypeAlias = Sequence[Sequence[_T]]
_Seq3D: TypeAlias = Sequence[Sequence[Sequence[_T]]]
_ListSeqND: TypeAlias = list[_T] | _SeqND[list[_T]]

_Tuple2: TypeAlias = tuple[_T, _T]
_Tuple3: TypeAlias = tuple[_T, _T, _T]
_Tuple4: TypeAlias = tuple[_T, _T, _T, _T]

_Mesh1: TypeAlias = tuple[_Array1D[_ScalarT]]
_Mesh2: TypeAlias = tuple[_Array2D[_ScalarT], _Array2D[_ScalarT1]]
_Mesh3: TypeAlias = tuple[_Array3D[_ScalarT], _Array3D[_ScalarT1], _Array3D[_ScalarT2]]

_IndexLike: TypeAlias = slice | _ArrayLikeInt_co

_Indexing: TypeAlias = L["ij", "xy"]
_InterpolationMethod = L[
    "inverted_cdf",
    "averaged_inverted_cdf",
    "closest_observation",
    "interpolated_inverted_cdf",
    "hazen",
    "weibull",
    "linear",
    "median_unbiased",
    "normal_unbiased",
    "lower",
    "higher",
    "midpoint",
    "nearest",
]

# The resulting value will be used as `y[cond] = func(vals, *args, **kw)`, so in can
# return any (usually 1d) array-like or scalar-like compatible with the input.
_PiecewiseFunction: TypeAlias = Callable[Concatenate[NDArray[_ScalarT], _Tss], ArrayLike]
_PiecewiseFunctions: TypeAlias = _SizedIterable[_PiecewiseFunction[_ScalarT, _Tss] | _ScalarLike_co]

@type_check_only
class _TrimZerosSequence(Protocol[_T_co]):
    def __len__(self, /) -> int: ...
    @overload
    def __getitem__(self, key: int, /) -> object: ...
    @overload
    def __getitem__(self, key: slice, /) -> _T_co: ...

@type_check_only
class _SupportsRMulFloat(Protocol[_T_co]):
    def __rmul__(self, other: float, /) -> _T_co: ...

@type_check_only
class _SizedIterable(Protocol[_T_co]):
    def __iter__(self) -> Iterable[_T_co]: ...
    def __len__(self) -> int: ...

###

class vectorize:
    __doc__: str | None
    __module__: L["numpy"] = "numpy"
    pyfunc: Callable[..., Incomplete]
    cache: bool
    signature: str | None
    otypes: str | None
    excluded: set[int | str]

    def __init__(
        self,
        /,
        pyfunc: Callable[..., Incomplete] | _NoValueType = ...,  # = _NoValue
        otypes: str | Iterable[DTypeLike] | None = None,
        doc: str | None = None,
        excluded: Iterable[int | str] | None = None,
        cache: bool = False,
        signature: str | None = None,
    ) -> None: ...
    def __call__(self, /, *args: Incomplete, **kwargs: Incomplete) -> Incomplete: ...

@overload
def rot90(m: _ArrayT, k: int = 1, axes: tuple[int, int] = (0, 1)) -> _ArrayT: ...
@overload
def rot90(m: _ArrayLike[_ScalarT], k: int = 1, axes: tuple[int, int] = (0, 1)) -> NDArray[_ScalarT]: ...
@overload
def rot90(m: ArrayLike, k: int = 1, axes: tuple[int, int] = (0, 1)) -> NDArray[Incomplete]: ...

# NOTE: Technically `flip` also accept scalars, but that has no effect and complicates
# the overloads significantly, so we ignore that case here.
@overload
def flip(m: _ArrayT, axis: int | tuple[int, ...] | None = None) -> _ArrayT: ...
@overload
def flip(m: _ArrayLike[_ScalarT], axis: int | tuple[int, ...] | None = None) -> NDArray[_ScalarT]: ...
@overload
def flip(m: ArrayLike, axis: int | tuple[int, ...] | None = None) -> NDArray[Incomplete]: ...

#
def iterable(y: object) -> TypeIs[Iterable[Any]]: ...

# NOTE: This assumes that if `axis` is given the input is at least 2d, and will
# therefore always return an array.
# NOTE: This assumes that if `keepdims=True` the input is at least 1d, and will
# therefore always return an array.
@overload  # inexact array, keepdims=True
def average(
    a: _ArrayInexactT,
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[True],
) -> _ArrayInexactT: ...
@overload  # inexact array, returned=True keepdims=True
def average(
    a: _ArrayInexactT,
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[True],
) -> _Tuple2[_ArrayInexactT]: ...
@overload  # inexact array-like, axis=None
def average(
    a: _ArrayLike[_InexactT],
    axis: None = None,
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> _InexactT: ...
@overload  # inexact array-like, axis=<given>
def average(
    a: _ArrayLike[_InexactT],
    axis: int | tuple[int, ...],
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> NDArray[_InexactT]: ...
@overload  # inexact array-like, keepdims=True
def average(
    a: _ArrayLike[_InexactT],
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[True],
) -> NDArray[_InexactT]: ...
@overload  # inexact array-like, axis=None, returned=True
def average(
    a: _ArrayLike[_InexactT],
    axis: None = None,
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[_InexactT]: ...
@overload  # inexact array-like, axis=<given>, returned=True
def average(
    a: _ArrayLike[_InexactT],
    axis: int | tuple[int, ...],
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[NDArray[_InexactT]]: ...
@overload  # inexact array-like, returned=True, keepdims=True
def average(
    a: _ArrayLike[_InexactT],
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[True],
) -> _Tuple2[NDArray[_InexactT]]: ...
@overload  # bool or integer array-like, axis=None
def average(
    a: _SeqND[float] | _ArrayLikeInt_co,
    axis: None = None,
    weights: _ArrayLikeFloat_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> np.float64: ...
@overload  # bool or integer array-like, axis=<given>
def average(
    a: _SeqND[float] | _ArrayLikeInt_co,
    axis: int | tuple[int, ...],
    weights: _ArrayLikeFloat_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> NDArray[np.float64]: ...
@overload  # bool or integer array-like, keepdims=True
def average(
    a: _SeqND[float] | _ArrayLikeInt_co,
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeFloat_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[True],
) -> NDArray[np.float64]: ...
@overload  # bool or integer array-like, axis=None, returned=True
def average(
    a: _SeqND[float] | _ArrayLikeInt_co,
    axis: None = None,
    weights: _ArrayLikeFloat_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[np.float64]: ...
@overload  # bool or integer array-like, axis=<given>, returned=True
def average(
    a: _SeqND[float] | _ArrayLikeInt_co,
    axis: int | tuple[int, ...],
    weights: _ArrayLikeFloat_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[NDArray[np.float64]]: ...
@overload  # bool or integer array-like, returned=True, keepdims=True
def average(
    a: _SeqND[float] | _ArrayLikeInt_co,
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeFloat_co | None = None,
    *,
    returned: L[True],
    keepdims: L[True],
) -> _Tuple2[NDArray[np.float64]]: ...
@overload  # complex array-like, axis=None
def average(
    a: _ListSeqND[complex],
    axis: None = None,
    weights: _ArrayLikeComplex_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> np.complex128: ...
@overload  # complex array-like, axis=<given>
def average(
    a: _ListSeqND[complex],
    axis: int | tuple[int, ...],
    weights: _ArrayLikeComplex_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> NDArray[np.complex128]: ...
@overload  # complex array-like, keepdims=True
def average(
    a: _ListSeqND[complex],
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeComplex_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[True],
) -> NDArray[np.complex128]: ...
@overload  # complex array-like, axis=None, returned=True
def average(
    a: _ListSeqND[complex],
    axis: None = None,
    weights: _ArrayLikeComplex_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[np.complex128]: ...
@overload  # complex array-like, axis=<given>, returned=True
def average(
    a: _ListSeqND[complex],
    axis: int | tuple[int, ...],
    weights: _ArrayLikeComplex_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[NDArray[np.complex128]]: ...
@overload  # complex array-like, keepdims=True, returned=True
def average(
    a: _ListSeqND[complex],
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeComplex_co | None = None,
    *,
    returned: L[True],
    keepdims: L[True],
) -> _Tuple2[NDArray[np.complex128]]: ...
@overload  # unknown, axis=None
def average(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    axis: None = None,
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> Any: ...
@overload  # unknown, axis=<given>
def average(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    axis: int | tuple[int, ...],
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[False] | _NoValueType = ...,
) -> np.ndarray: ...
@overload  # unknown, keepdims=True
def average(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeNumber_co | None = None,
    returned: L[False] = False,
    *,
    keepdims: L[True],
) -> np.ndarray: ...
@overload  # unknown, axis=None, returned=True
def average(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    axis: None = None,
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[Any]: ...
@overload  # unknown, axis=<given>, returned=True
def average(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    axis: int | tuple[int, ...],
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[False] | _NoValueType = ...,
) -> _Tuple2[np.ndarray]: ...
@overload  # unknown, returned=True, keepdims=True
def average(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    axis: int | tuple[int, ...] | None = None,
    weights: _ArrayLikeNumber_co | None = None,
    *,
    returned: L[True],
    keepdims: L[True],
) -> _Tuple2[np.ndarray]: ...

#
@overload
def asarray_chkfinite(a: _ArrayT, dtype: None = None, order: _OrderKACF = None) -> _ArrayT: ...
@overload
def asarray_chkfinite(
    a: np.ndarray[_ShapeT], dtype: _DTypeLike[_ScalarT], order: _OrderKACF = None
) -> _Array[_ShapeT, _ScalarT]: ...
@overload
def asarray_chkfinite(a: _ArrayLike[_ScalarT], dtype: None = None, order: _OrderKACF = None) -> NDArray[_ScalarT]: ...
@overload
def asarray_chkfinite(a: object, dtype: _DTypeLike[_ScalarT], order: _OrderKACF = None) -> NDArray[_ScalarT]: ...
@overload
def asarray_chkfinite(a: object, dtype: DTypeLike | None = None, order: _OrderKACF = None) -> NDArray[Incomplete]: ...

# NOTE: Contrary to the documentation, scalars are also accepted and treated as
# `[condlist]`. And even though the documentation says these should be boolean, in
# practice anything that `np.array(condlist, dtype=bool)` accepts will work, i.e. any
# array-like.
@overload
def piecewise(
    x: _Array[_ShapeT, _ScalarT],
    condlist: ArrayLike,
    funclist: _PiecewiseFunctions[Any, _Tss],
    *args: _Tss.args,
    **kw: _Tss.kwargs,
) -> _Array[_ShapeT, _ScalarT]: ...
@overload
def piecewise(
    x: _ArrayLike[_ScalarT],
    condlist: ArrayLike,
    funclist: _PiecewiseFunctions[Any, _Tss],
    *args: _Tss.args,
    **kw: _Tss.kwargs,
) -> NDArray[_ScalarT]: ...
@overload
def piecewise(
    x: ArrayLike,
    condlist: ArrayLike,
    funclist: _PiecewiseFunctions[_ScalarT, _Tss],
    *args: _Tss.args,
    **kw: _Tss.kwargs,
) -> NDArray[_ScalarT]: ...

# NOTE: condition is usually boolean, but anything with zero/non-zero semantics works
@overload
def extract(condition: ArrayLike, arr: _ArrayLike[_ScalarT]) -> _Array1D[_ScalarT]: ...
@overload
def extract(condition: ArrayLike, arr: _SeqND[bool]) -> _Array1D[np.bool]: ...
@overload
def extract(condition: ArrayLike, arr: _ListSeqND[int]) -> _Array1D[np.int_]: ...
@overload
def extract(condition: ArrayLike, arr: _ListSeqND[float]) -> _Array1D[np.float64]: ...
@overload
def extract(condition: ArrayLike, arr: _ListSeqND[complex]) -> _Array1D[np.complex128]: ...
@overload
def extract(condition: ArrayLike, arr: _SeqND[bytes]) -> _Array1D[np.bytes_]: ...
@overload
def extract(condition: ArrayLike, arr: _SeqND[str]) -> _Array1D[np.str_]: ...
@overload
def extract(condition: ArrayLike, arr: ArrayLike) -> _Array1D[Incomplete]: ...

# NOTE: unlike `extract`, passing non-boolean conditions for `condlist` will raise an
# error at runtime
@overload
def select(
    condlist: _SizedIterable[_ArrayLikeBool_co],
    choicelist: Sequence[_ArrayT],
    default: ArrayLike = 0,
) -> _ArrayT: ...
@overload
def select(
    condlist: _SizedIterable[_ArrayLikeBool_co],
    choicelist: Sequence[_ArrayLike[_ScalarT]] | NDArray[_ScalarT],
    default: ArrayLike = 0,
) -> NDArray[_ScalarT]: ...
@overload
def select(
    condlist: _SizedIterable[_ArrayLikeBool_co],
    choicelist: Sequence[ArrayLike],
    default: ArrayLike = 0,
) -> np.ndarray: ...

# keep roughly in sync with `ma.core.copy`
@overload
def copy(a: _ArrayT, order: _OrderKACF, subok: L[True]) -> _ArrayT: ...
@overload
def copy(a: _ArrayT, order: _OrderKACF = "K", *, subok: L[True]) -> _ArrayT: ...
@overload
def copy(a: _ArrayLike[_ScalarT], order: _OrderKACF = "K", subok: L[False] = False) -> NDArray[_ScalarT]: ...
@overload
def copy(a: ArrayLike, order: _OrderKACF = "K", subok: L[False] = False) -> NDArray[Incomplete]: ...

#
@overload  # ?d, known inexact scalar-type
def gradient(
    f: _ArrayNoD[_InexactTimeT],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
    # `| Any` instead of ` | tuple` is returned to avoid several mypy_primer errors
) -> _Array1D[_InexactTimeT] | Any: ...
@overload  # 1d, known inexact scalar-type
def gradient(
    f: _Array1D[_InexactTimeT],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Array1D[_InexactTimeT]: ...
@overload  # 2d, known inexact scalar-type
def gradient(
    f: _Array2D[_InexactTimeT],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh2[_InexactTimeT, _InexactTimeT]: ...
@overload  # 3d, known inexact scalar-type
def gradient(
    f: _Array3D[_InexactTimeT],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh3[_InexactTimeT, _InexactTimeT, _InexactTimeT]: ...
@overload  # ?d, datetime64 scalar-type
def gradient(
    f: _ArrayNoD[np.datetime64],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Array1D[np.timedelta64] | tuple[NDArray[np.timedelta64], ...]: ...
@overload  # 1d, datetime64 scalar-type
def gradient(
    f: _Array1D[np.datetime64],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Array1D[np.timedelta64]: ...
@overload  # 2d, datetime64 scalar-type
def gradient(
    f: _Array2D[np.datetime64],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh2[np.timedelta64, np.timedelta64]: ...
@overload  # 3d, datetime64 scalar-type
def gradient(
    f: _Array3D[np.datetime64],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh3[np.timedelta64, np.timedelta64, np.timedelta64]: ...
@overload  # 1d float-like
def gradient(
    f: _Seq1D[float],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Array1D[np.float64]: ...
@overload  # 2d float-like
def gradient(
    f: _Seq2D[float],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh2[np.float64, np.float64]: ...
@overload  # 3d float-like
def gradient(
    f: _Seq3D[float],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh3[np.float64, np.float64, np.float64]: ...
@overload  # 1d complex-like  (the `list` avoids overlap with the float-like overload)
def gradient(
    f: list[complex],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Array1D[np.complex128]: ...
@overload  # 2d float-like
def gradient(
    f: _Seq1D[list[complex]],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh2[np.complex128, np.complex128]: ...
@overload  # 3d float-like
def gradient(
    f: _Seq2D[list[complex]],
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> _Mesh3[np.complex128, np.complex128, np.complex128]: ...
@overload  # fallback
def gradient(
    f: ArrayLike,
    *varargs: _ArrayLikeNumber_co,
    axis: _ShapeLike | None = None,
    edge_order: L[1, 2] = 1,
) -> Incomplete: ...

#
@overload  # n == 0; return input unchanged
def diff(
    a: _T,
    n: L[0],
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,  # = _NoValue
    append: ArrayLike | _NoValueType = ...,  # = _NoValue
) -> _T: ...
@overload  # known array-type
def diff(
    a: _ArrayNumericT,
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _ArrayNumericT: ...
@overload  # known shape, datetime64
def diff(
    a: _Array[_ShapeT, np.datetime64],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array[_ShapeT, np.timedelta64]: ...
@overload  # unknown shape, known scalar-type
def diff(
    a: _ArrayLike[_ScalarNumericT],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> NDArray[_ScalarNumericT]: ...
@overload  # unknown shape, datetime64
def diff(
    a: _ArrayLike[np.datetime64],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> NDArray[np.timedelta64]: ...
@overload  # 1d int
def diff(
    a: _Seq1D[int],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array1D[np.int_]: ...
@overload  # 2d int
def diff(
    a: _Seq2D[int],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array2D[np.int_]: ...
@overload  # 1d float  (the `list` avoids overlap with the `int` overloads)
def diff(
    a: list[float],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array1D[np.float64]: ...
@overload  # 2d float
def diff(
    a: _Seq1D[list[float]],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array2D[np.float64]: ...
@overload  # 1d complex  (the `list` avoids overlap with the `int` overloads)
def diff(
    a: list[complex],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array1D[np.complex128]: ...
@overload  # 2d complex
def diff(
    a: _Seq1D[list[complex]],
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> _Array2D[np.complex128]: ...
@overload  # unknown shape, unknown scalar-type
def diff(
    a: ArrayLike,
    n: int = 1,
    axis: SupportsIndex = -1,
    prepend: ArrayLike | _NoValueType = ...,
    append: ArrayLike | _NoValueType = ...,
) -> NDArray[Incomplete]: ...

#
@overload  # float scalar
def interp(
    x: _FloatLike_co,
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLikeFloat_co,
    left: _FloatLike_co | None = None,
    right: _FloatLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> np.float64: ...
@overload  # complex scalar
def interp(
    x: _FloatLike_co,
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLike1D[np.complexfloating] | list[complex],
    left: _NumberLike_co | None = None,
    right: _NumberLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> np.complex128: ...
@overload  # float array
def interp(
    x: _Array[_ShapeT, _floating_co],
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLikeFloat_co,
    left: _FloatLike_co | None = None,
    right: _FloatLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> _Array[_ShapeT, np.float64]: ...
@overload  # complex array
def interp(
    x: _Array[_ShapeT, _floating_co],
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLike1D[np.complexfloating] | list[complex],
    left: _NumberLike_co | None = None,
    right: _NumberLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> _Array[_ShapeT, np.complex128]: ...
@overload  # float sequence
def interp(
    x: _Seq1D[_FloatLike_co],
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLikeFloat_co,
    left: _FloatLike_co | None = None,
    right: _FloatLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> _Array1D[np.float64]: ...
@overload  # complex sequence
def interp(
    x: _Seq1D[_FloatLike_co],
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLike1D[np.complexfloating] | list[complex],
    left: _NumberLike_co | None = None,
    right: _NumberLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> _Array1D[np.complex128]: ...
@overload  # float array-like
def interp(
    x: _SeqND[_FloatLike_co],
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLikeFloat_co,
    left: _FloatLike_co | None = None,
    right: _FloatLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # complex array-like
def interp(
    x: _SeqND[_FloatLike_co],
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLike1D[np.complexfloating] | list[complex],
    left: _NumberLike_co | None = None,
    right: _NumberLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # float scalar/array-like
def interp(
    x: _ArrayLikeFloat_co,
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLikeFloat_co,
    left: _FloatLike_co | None = None,
    right: _FloatLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> NDArray[np.float64] | np.float64: ...
@overload  # complex scalar/array-like
def interp(
    x: _ArrayLikeFloat_co,
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLike1D[np.complexfloating],
    left: _NumberLike_co | None = None,
    right: _NumberLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> NDArray[np.complex128] | np.complex128: ...
@overload  # float/complex scalar/array-like
def interp(
    x: _ArrayLikeFloat_co,
    xp: _ArrayLikeFloat_co,
    fp: _ArrayLikeNumber_co,
    left: _NumberLike_co | None = None,
    right: _NumberLike_co | None = None,
    period: _FloatLike_co | None = None,
) -> NDArray[np.complex128 | np.float64] | np.complex128 | np.float64: ...

#
@overload  # 0d T: floating -> 0d T
def angle(z: _FloatingT, deg: bool = False) -> _FloatingT: ...
@overload  # 0d complex | float | ~integer -> 0d float64
def angle(z: complex | _integer_co, deg: bool = False) -> np.float64: ...
@overload  # 0d complex64 -> 0d float32
def angle(z: np.complex64, deg: bool = False) -> np.float32: ...
@overload  # 0d clongdouble -> 0d longdouble
def angle(z: np.clongdouble, deg: bool = False) -> np.longdouble: ...
@overload  # T: nd floating -> T
def angle(z: _ArrayFloatingT, deg: bool = False) -> _ArrayFloatingT: ...
@overload  # nd T: complex128 | ~integer -> nd float64
def angle(z: _Array[_ShapeT, np.complex128 | _integer_co], deg: bool = False) -> _Array[_ShapeT, np.float64]: ...
@overload  # nd T: complex64 -> nd float32
def angle(z: _Array[_ShapeT, np.complex64], deg: bool = False) -> _Array[_ShapeT, np.float32]: ...
@overload  # nd T: clongdouble -> nd longdouble
def angle(z: _Array[_ShapeT, np.clongdouble], deg: bool = False) -> _Array[_ShapeT, np.longdouble]: ...
@overload  # 1d complex -> 1d float64
def angle(z: _Seq1D[complex], deg: bool = False) -> _Array1D[np.float64]: ...
@overload  # 2d complex -> 2d float64
def angle(z: _Seq2D[complex], deg: bool = False) -> _Array2D[np.float64]: ...
@overload  # 3d complex -> 3d float64
def angle(z: _Seq3D[complex], deg: bool = False) -> _Array3D[np.float64]: ...
@overload  # fallback
def angle(z: _ArrayLikeComplex_co, deg: bool = False) -> NDArray[np.floating] | Any: ...

#
@overload  # known array-type
def unwrap(
    p: _ArrayFloatObjT,
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> _ArrayFloatObjT: ...
@overload  # known shape, float64
def unwrap(
    p: _Array[_ShapeT, _float64_co],
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> _Array[_ShapeT, np.float64]: ...
@overload  # 1d float64-like
def unwrap(
    p: _Seq1D[float | _float64_co],
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> _Array1D[np.float64]: ...
@overload  # 2d float64-like
def unwrap(
    p: _Seq2D[float | _float64_co],
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> _Array2D[np.float64]: ...
@overload  # 3d float64-like
def unwrap(
    p: _Seq3D[float | _float64_co],
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> _Array3D[np.float64]: ...
@overload  # ?d, float64
def unwrap(
    p: _SeqND[float] | _ArrayLike[_float64_co],
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> NDArray[np.float64]: ...
@overload  # fallback
def unwrap(
    p: _ArrayLikeFloat_co | _ArrayLikeObject_co,
    discont: float | None = None,
    axis: int = -1,
    *,
    period: float = ...,  # = τ
) -> np.ndarray: ...

#
@overload
def sort_complex(a: _ArrayComplexT) -> _ArrayComplexT: ...
@overload  # complex64, shape known
def sort_complex(a: _Array[_ShapeT, np.int8 | np.uint8 | np.int16 | np.uint16]) -> _Array[_ShapeT, np.complex64]: ...
@overload  # complex64, shape unknown
def sort_complex(a: _ArrayLike[np.int8 | np.uint8 | np.int16 | np.uint16]) -> NDArray[np.complex64]: ...
@overload  # complex128, shape known
def sort_complex(a: _Array[_ShapeT, _SortsToComplex128]) -> _Array[_ShapeT, np.complex128]: ...
@overload  # complex128, shape unknown
def sort_complex(a: _ArrayLike[_SortsToComplex128]) -> NDArray[np.complex128]: ...
@overload  # clongdouble, shape known
def sort_complex(a: _Array[_ShapeT, np.longdouble]) -> _Array[_ShapeT, np.clongdouble]: ...
@overload  # clongdouble, shape unknown
def sort_complex(a: _ArrayLike[np.longdouble]) -> NDArray[np.clongdouble]: ...

#
def trim_zeros(filt: _TrimZerosSequence[_T], trim: L["f", "b", "fb", "bf"] = "fb", axis: _ShapeLike | None = None) -> _T: ...

# NOTE: keep in sync with `corrcoef`
@overload  # ?d, known inexact scalar-type >=64 precision, y=<given>.
def cov(
    m: _ArrayLike[_AnyDoubleT],
    y: _ArrayLike[_AnyDoubleT],
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: None = None,
) -> _Array2D[_AnyDoubleT]: ...
@overload  # ?d, known inexact scalar-type >=64 precision, y=None -> 0d or 2d
def cov(
    m: _ArrayNoD[_AnyDoubleT],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> NDArray[_AnyDoubleT]: ...
@overload  # 1d, known inexact scalar-type >=64 precision, y=None
def cov(
    m: _Array1D[_AnyDoubleT],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> _Array0D[_AnyDoubleT]: ...
@overload  # nd, known inexact scalar-type >=64 precision, y=None -> 0d or 2d
def cov(
    m: _ArrayLike[_AnyDoubleT],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> NDArray[_AnyDoubleT]: ...
@overload  # nd, casts to float64, y=<given>
def cov(
    m: NDArray[np.float32 | np.float16 | _integer_co] | _Seq1D[float] | _Seq2D[float],
    y: NDArray[np.float32 | np.float16 | _integer_co] | _Seq1D[float] | _Seq2D[float],
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> _Array2D[np.float64]: ...
@overload  # ?d or 2d, casts to float64, y=None -> 0d or 2d
def cov(
    m: _ArrayNoD[np.float32 | np.float16 | _integer_co] | _Seq2D[float],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> NDArray[np.float64]: ...
@overload  # 1d, casts to float64, y=None
def cov(
    m:  _Array1D[np.float32 | np.float16 | _integer_co] | _Seq1D[float],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> _Array0D[np.float64]: ...
@overload  # nd, casts to float64, y=None -> 0d or 2d
def cov(
    m:  _ArrayLike[np.float32 | np.float16 | _integer_co],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> NDArray[np.float64]: ...
@overload  # 1d complex, y=<given>  (`list` avoids overlap with float overloads)
def cov(
    m: list[complex] | _Seq1D[list[complex]],
    y: list[complex] | _Seq1D[list[complex]],
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.complex128] | None = None,
) -> _Array2D[np.complex128]: ...
@overload  # 1d complex, y=None
def cov(
    m: list[complex],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.complex128] | None = None,
) -> _Array0D[np.complex128]: ...
@overload  # 2d complex, y=None -> 0d or 2d
def cov(
    m: _Seq1D[list[complex]],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[np.complex128] | None = None,
) -> NDArray[np.complex128]: ...
@overload  # 1d complex-like, y=None, dtype=<known>
def cov(
    m: _Seq1D[_ComplexLike_co],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
) -> _Array0D[_ScalarT]: ...
@overload  # nd complex-like, y=<given>, dtype=<known>
def cov(
    m: _ArrayLikeComplex_co,
    y: _ArrayLikeComplex_co,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
) -> _Array2D[_ScalarT]: ...
@overload  # nd complex-like, y=None, dtype=<known> -> 0d or 2d
def cov(
    m: _ArrayLikeComplex_co,
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
) -> NDArray[_ScalarT]: ...
@overload  # nd complex-like, y=<given>, dtype=?
def cov(
    m: _ArrayLikeComplex_co,
    y: _ArrayLikeComplex_co,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: DTypeLike | None = None,
) -> _Array2D[Incomplete]: ...
@overload  # 1d complex-like, y=None, dtype=?
def cov(
    m: _Seq1D[_ComplexLike_co],
    y: None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: DTypeLike | None = None,
) -> _Array0D[Incomplete]: ...
@overload  # nd complex-like, dtype=?
def cov(
    m: _ArrayLikeComplex_co,
    y: _ArrayLikeComplex_co | None = None,
    rowvar: bool = True,
    bias: bool = False,
    ddof: SupportsIndex | SupportsInt | None = None,
    fweights: _ArrayLikeInt_co | None = None,
    aweights: _ArrayLikeFloat_co | None = None,
    *,
    dtype: DTypeLike | None = None,
) -> NDArray[Incomplete]: ...

# NOTE: If only `x` is given and the resulting array has shape (1,1), a bare scalar
# is returned instead of a 2D array. When y is given, a 2D array is always returned.
# This differs from `cov`, which returns 0-D arrays instead of scalars in such cases.
# NOTE: keep in sync with `cov`
@overload  # ?d, known inexact scalar-type >=64 precision, y=<given>.
def corrcoef(
    x: _ArrayLike[_AnyDoubleT],
    y: _ArrayLike[_AnyDoubleT],
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> _Array2D[_AnyDoubleT]: ...
@overload  # ?d, known inexact scalar-type >=64 precision, y=None
def corrcoef(
    x: _ArrayNoD[_AnyDoubleT],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> _Array2D[_AnyDoubleT] | _AnyDoubleT: ...
@overload  # 1d, known inexact scalar-type >=64 precision, y=None
def corrcoef(
    x: _Array1D[_AnyDoubleT],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> _AnyDoubleT: ...
@overload  # nd, known inexact scalar-type >=64 precision, y=None
def corrcoef(
    x: _ArrayLike[_AnyDoubleT],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_AnyDoubleT] | None = None,
) -> _Array2D[_AnyDoubleT] | _AnyDoubleT: ...
@overload  # nd, casts to float64, y=<given>
def corrcoef(
    x: NDArray[np.float32 | np.float16 | _integer_co] | _Seq1D[float] | _Seq2D[float],
    y: NDArray[np.float32 | np.float16 | _integer_co] | _Seq1D[float] | _Seq2D[float],
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> _Array2D[np.float64]: ...
@overload  # ?d or 2d, casts to float64, y=None
def corrcoef(
    x: _ArrayNoD[np.float32 | np.float16 | _integer_co] | _Seq2D[float],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> _Array2D[np.float64] | np.float64: ...
@overload  # 1d, casts to float64, y=None
def corrcoef(
    x: _Array1D[np.float32 | np.float16 | _integer_co] | _Seq1D[float],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> np.float64: ...
@overload  # nd, casts to float64, y=None
def corrcoef(
    x: _ArrayLike[np.float32 | np.float16 | _integer_co],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.float64] | None = None,
) -> _Array2D[np.float64] | np.float64: ...
@overload  # 1d complex, y=<given>  (`list` avoids overlap with float overloads)
def corrcoef(
    x: list[complex] | _Seq1D[list[complex]],
    y: list[complex] | _Seq1D[list[complex]],
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.complex128] | None = None,
) -> _Array2D[np.complex128]: ...
@overload  # 1d complex, y=None
def corrcoef(
    x: list[complex],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.complex128] | None = None,
) -> np.complex128: ...
@overload  # 2d complex, y=None
def corrcoef(
    x: _Seq1D[list[complex]],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[np.complex128] | None = None,
) -> _Array2D[np.complex128] | np.complex128: ...
@overload  # 1d complex-like, y=None, dtype=<known>
def corrcoef(
    x: _Seq1D[_ComplexLike_co],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_ScalarT],
) -> _ScalarT: ...
@overload  # nd complex-like, y=<given>, dtype=<known>
def corrcoef(
    x: _ArrayLikeComplex_co,
    y: _ArrayLikeComplex_co,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_ScalarT],
) -> _Array2D[_ScalarT]: ...
@overload  # nd complex-like, y=None, dtype=<known>
def corrcoef(
    x: _ArrayLikeComplex_co,
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: _DTypeLike[_ScalarT],
) -> _Array2D[_ScalarT] | _ScalarT: ...
@overload  # nd complex-like, y=<given>, dtype=?
def corrcoef(
    x: _ArrayLikeComplex_co,
    y: _ArrayLikeComplex_co,
    rowvar: bool = True,
    *,
    dtype: DTypeLike | None = None,
) -> _Array2D[Incomplete]: ...
@overload  # 1d complex-like, y=None, dtype=?
def corrcoef(
    x: _Seq1D[_ComplexLike_co],
    y: None = None,
    rowvar: bool = True,
    *,
    dtype: DTypeLike | None = None,
) -> Incomplete: ...
@overload  # nd complex-like, dtype=?
def corrcoef(
    x: _ArrayLikeComplex_co,
    y: _ArrayLikeComplex_co | None = None,
    rowvar: bool = True,
    *,
    dtype: DTypeLike | None = None,
) -> _Array2D[Incomplete] | Incomplete: ...

# note that floating `M` are accepted, but their fractional part is ignored
def blackman(M: _FloatLike_co) -> _Array1D[np.float64]: ...
def bartlett(M: _FloatLike_co) -> _Array1D[np.float64]: ...
def hanning(M: _FloatLike_co) -> _Array1D[np.float64]: ...
def hamming(M: _FloatLike_co) -> _Array1D[np.float64]: ...
def kaiser(M: _FloatLike_co, beta: _FloatLike_co) -> _Array1D[np.float64]: ...

#
@overload
def i0(x: _Array[_ShapeT, np.floating | np.integer]) -> _Array[_ShapeT, np.float64]: ...
@overload
def i0(x: _FloatLike_co) -> _Array0D[np.float64]: ...
@overload
def i0(x: _Seq1D[_FloatLike_co]) -> _Array1D[np.float64]: ...
@overload
def i0(x: _Seq2D[_FloatLike_co]) -> _Array2D[np.float64]: ...
@overload
def i0(x: _Seq3D[_FloatLike_co]) -> _Array3D[np.float64]: ...
@overload
def i0(x: _ArrayLikeFloat_co) -> NDArray[np.float64]: ...

#
@overload
def sinc(x: _InexactT) -> _InexactT: ...
@overload
def sinc(x: float | _float64_co) -> np.float64: ...
@overload
def sinc(x: complex) -> np.complex128 | Any: ...
@overload
def sinc(x: _ArrayInexactT) -> _ArrayInexactT: ...
@overload
def sinc(x: _Array[_ShapeT, _integer_co]) -> _Array[_ShapeT, np.float64]: ...
@overload
def sinc(x: _Seq1D[float]) -> _Array1D[np.float64]: ...
@overload
def sinc(x: _Seq2D[float]) -> _Array2D[np.float64]: ...
@overload
def sinc(x: _Seq3D[float]) -> _Array3D[np.float64]: ...
@overload
def sinc(x: _SeqND[float]) -> NDArray[np.float64]: ...
@overload
def sinc(x: list[complex]) -> _Array1D[np.complex128]: ...
@overload
def sinc(x: _Seq1D[list[complex]]) -> _Array2D[np.complex128]: ...
@overload
def sinc(x: _Seq2D[list[complex]]) -> _Array3D[np.complex128]: ...
@overload
def sinc(x: _ArrayLikeComplex_co) -> np.ndarray | Any: ...

# NOTE: We assume that `axis` is only provided for >=1-D arrays because for <1-D arrays
# it has no effect, and would complicate the overloads significantly.
@overload  # known scalar-type, keepdims=False (default)
def median(
    a: _ArrayLike[_InexactTimeT],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: L[False] = False,
) -> _InexactTimeT: ...
@overload  # float array-like, keepdims=False (default)
def median(
    a: _ArrayLikeInt_co | _SeqND[float] | float,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: L[False] = False,
) -> np.float64: ...
@overload  # complex array-like, keepdims=False (default)
def median(
    a: _ListSeqND[complex],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: L[False] = False,
) -> np.complex128: ...
@overload  # complex scalar, keepdims=False (default)
def median(
    a: complex,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: L[False] = False,
) -> np.complex128 | Any: ...
@overload  # known array-type, keepdims=True
def median(
    a: _ArrayNumericT,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    *,
    keepdims: L[True],
) -> _ArrayNumericT: ...
@overload  # known scalar-type, keepdims=True
def median(
    a: _ArrayLike[_ScalarNumericT],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    *,
    keepdims: L[True],
) -> NDArray[_ScalarNumericT]: ...
@overload  # known scalar-type, axis=<given>
def median(
    a: _ArrayLike[_ScalarNumericT],
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: bool = False,
) -> NDArray[_ScalarNumericT]: ...
@overload  # float array-like, keepdims=True
def median(
    a: _SeqND[float],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    *,
    keepdims: L[True],
) -> NDArray[np.float64]: ...
@overload  # float array-like, axis=<given>
def median(
    a: _SeqND[float],
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: bool = False,
) -> NDArray[np.float64]: ...
@overload  # complex array-like, keepdims=True
def median(
    a: _ListSeqND[complex],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    *,
    keepdims: L[True],
) -> NDArray[np.complex128]: ...
@overload  # complex array-like, axis=<given>
def median(
    a: _ListSeqND[complex],
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: bool = False,
) -> NDArray[np.complex128]: ...
@overload  # out=<given> (keyword)
def median(
    a: _ArrayLikeComplex_co | _ArrayLike[np.timedelta64 | np.object_],
    axis: _ShapeLike | None = None,
    *,
    out: _ArrayT,
    overwrite_input: bool = False,
    keepdims: bool = False,
) -> _ArrayT: ...
@overload  # out=<given> (positional)
def median(
    a: _ArrayLikeComplex_co | _ArrayLike[np.timedelta64 | np.object_],
    axis: _ShapeLike | None,
    out: _ArrayT,
    overwrite_input: bool = False,
    keepdims: bool = False,
) -> _ArrayT: ...
@overload  # fallback
def median(
    a: _ArrayLikeComplex_co | _ArrayLike[np.timedelta64 | np.object_],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    keepdims: bool = False,
) -> Incomplete: ...

# NOTE: keep in sync with `quantile`
@overload  # inexact, scalar, axis=None
def percentile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _InexactDateTimeT: ...
@overload  # inexact, scalar, axis=<given>
def percentile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[_InexactDateTimeT]: ...
@overload  # inexact, scalar, keepdims=True
def percentile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[_InexactDateTimeT]: ...
@overload  # inexact, array, axis=None
def percentile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, _InexactDateTimeT]: ...
@overload  # inexact, array-like
def percentile(
    a: _ArrayLike[_InexactDateTimeT],
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[_InexactDateTimeT]: ...
@overload  # float, scalar, axis=None
def percentile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> np.float64: ...
@overload  # float, scalar, axis=<given>
def percentile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # float, scalar, keepdims=True
def percentile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # float, array, axis=None
def percentile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, np.float64]: ...
@overload  # float, array-like
def percentile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # complex, scalar, axis=None
def percentile(
    a: _ListSeqND[complex],
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> np.complex128: ...
@overload  # complex, scalar, axis=<given>
def percentile(
    a: _ListSeqND[complex],
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # complex, scalar, keepdims=True
def percentile(
    a: _ListSeqND[complex],
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # complex, array, axis=None
def percentile(
    a: _ListSeqND[complex],
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, np.complex128]: ...
@overload  # complex, array-like
def percentile(
    a: _ListSeqND[complex],
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # object_, scalar, axis=None
def percentile(
    a: _ArrayLikeObject_co,
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> Any: ...
@overload  # object_, scalar, axis=<given>
def percentile(
    a: _ArrayLikeObject_co,
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.object_]: ...
@overload  # object_, scalar, keepdims=True
def percentile(
    a: _ArrayLikeObject_co,
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.object_]: ...
@overload  # object_, array, axis=None
def percentile(
    a: _ArrayLikeObject_co,
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, np.object_]: ...
@overload  # object_, array-like
def percentile(
    a: _ArrayLikeObject_co,
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.object_]: ...
@overload  # out=<given> (keyword)
def percentile(
    a: ArrayLike,
    q: _ArrayLikeFloat_co,
    axis: _ShapeLike | None,
    out: _ArrayT,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _ArrayT: ...
@overload  # out=<given> (positional)
def percentile(
    a: ArrayLike,
    q: _ArrayLikeFloat_co,
    axis: _ShapeLike | None = None,
    *,
    out: _ArrayT,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    weights: _ArrayLikeFloat_co | None = None,
) -> _ArrayT: ...
@overload  # fallback
def percentile(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    q: _ArrayLikeFloat_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> Incomplete: ...

# NOTE: keep in sync with `percentile`
@overload  # inexact, scalar, axis=None
def quantile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _InexactDateTimeT: ...
@overload  # inexact, scalar, axis=<given>
def quantile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[_InexactDateTimeT]: ...
@overload  # inexact, scalar, keepdims=True
def quantile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[_InexactDateTimeT]: ...
@overload  # inexact, array, axis=None
def quantile(
    a: _ArrayLike[_InexactDateTimeT],
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, _InexactDateTimeT]: ...
@overload  # inexact, array-like
def quantile(
    a: _ArrayLike[_InexactDateTimeT],
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[_InexactDateTimeT]: ...
@overload  # float, scalar, axis=None
def quantile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> np.float64: ...
@overload  # float, scalar, axis=<given>
def quantile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # float, scalar, keepdims=True
def quantile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # float, array, axis=None
def quantile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, np.float64]: ...
@overload  # float, array-like
def quantile(
    a: _SeqND[float] | _ArrayLikeInt_co,
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.float64]: ...
@overload  # complex, scalar, axis=None
def quantile(
    a: _ListSeqND[complex],
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> np.complex128: ...
@overload  # complex, scalar, axis=<given>
def quantile(
    a: _ListSeqND[complex],
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # complex, scalar, keepdims=True
def quantile(
    a: _ListSeqND[complex],
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # complex, array, axis=None
def quantile(
    a: _ListSeqND[complex],
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, np.complex128]: ...
@overload  # complex, array-like
def quantile(
    a: _ListSeqND[complex],
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.complex128]: ...
@overload  # object_, scalar, axis=None
def quantile(
    a: _ArrayLikeObject_co,
    q: _FloatLike_co,
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> Any: ...
@overload  # object_, scalar, axis=<given>
def quantile(
    a: _ArrayLikeObject_co,
    q: _FloatLike_co,
    axis: _ShapeLike,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.object_]: ...
@overload  # object_, scalar, keepdims=True
def quantile(
    a: _ArrayLikeObject_co,
    q: _FloatLike_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    *,
    keepdims: L[True],
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.object_]: ...
@overload  # object_, array, axis=None
def quantile(
    a: _ArrayLikeObject_co,
    q: _Array[_ShapeT, _floating_co],
    axis: None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: L[False] = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _Array[_ShapeT, np.object_]: ...
@overload  # object_, array-like
def quantile(
    a: _ArrayLikeObject_co,
    q: NDArray[_floating_co] | _SeqND[_FloatLike_co],
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> NDArray[np.object_]: ...
@overload  # out=<given> (keyword)
def quantile(
    a: ArrayLike,
    q: _ArrayLikeFloat_co,
    axis: _ShapeLike | None,
    out: _ArrayT,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> _ArrayT: ...
@overload  # out=<given> (positional)
def quantile(
    a: ArrayLike,
    q: _ArrayLikeFloat_co,
    axis: _ShapeLike | None = None,
    *,
    out: _ArrayT,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    weights: _ArrayLikeFloat_co | None = None,
) -> _ArrayT: ...
@overload  # fallback
def quantile(
    a: _ArrayLikeNumber_co | _ArrayLikeObject_co,
    q: _ArrayLikeFloat_co,
    axis: _ShapeLike | None = None,
    out: None = None,
    overwrite_input: bool = False,
    method: _InterpolationMethod = "linear",
    keepdims: bool = False,
    *,
    weights: _ArrayLikeFloat_co | None = None,
) -> Incomplete: ...

#
@overload  # ?d, known inexact/timedelta64 scalar-type
def trapezoid(
    y: _ArrayNoD[_InexactTimeT],
    x: _ArrayLike[_InexactTimeT] | _ArrayLikeFloat_co | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[_InexactTimeT] | _InexactTimeT: ...
@overload  # ?d, casts to float64
def trapezoid(
    y: _ArrayNoD[_integer_co],
    x: _ArrayLikeFloat_co | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[np.float64] | np.float64: ...
@overload  # strict 1d, known inexact/timedelta64 scalar-type
def trapezoid(
    y: _Array1D[_InexactTimeT],
    x: _Array1D[_InexactTimeT] | _Seq1D[float] | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> _InexactTimeT: ...
@overload  # strict 1d, casts to float64
def trapezoid(
    y: _Array1D[_float64_co] | _Seq1D[float],
    x: _Array1D[_float64_co] | _Seq1D[float] | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> np.float64: ...
@overload  # strict 1d, casts to complex128 (`list` prevents overlapping overloads)
def trapezoid(
    y: list[complex],
    x: _Seq1D[complex] | None = None,
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> np.complex128: ...
@overload  # strict 1d, casts to complex128
def trapezoid(
    y: _Seq1D[complex],
    x: list[complex],
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> np.complex128: ...
@overload  # strict 2d, known inexact/timedelta64 scalar-type
def trapezoid(
    y: _Array2D[_InexactTimeT],
    x: _ArrayMax2D[_InexactTimeT] | _Seq2D[float] | _Seq1D[float] | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> _InexactTimeT: ...
@overload  # strict 2d, casts to float64
def trapezoid(
    y: _Array2D[_float64_co] | _Seq2D[float],
    x: _ArrayMax2D[_float64_co] | _Seq2D[float] | _Seq1D[float] | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> np.float64: ...
@overload  # strict 2d, casts to complex128 (`list` prevents overlapping overloads)
def trapezoid(
    y: _Seq1D[list[complex]],
    x: _Seq2D[complex] | _Seq1D[complex] | None = None,
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> np.complex128: ...
@overload  # strict 2d, casts to complex128
def trapezoid(
    y: _Seq2D[complex] | _Seq1D[complex],
    x: _Seq1D[list[complex]],
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> np.complex128: ...
@overload
def trapezoid(
    y: _ArrayLike[_InexactTimeT],
    x: _ArrayLike[_InexactTimeT] | _ArrayLikeInt_co | None = None,
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[_InexactTimeT] | _InexactTimeT: ...
@overload
def trapezoid(
    y: _ArrayLike[_float64_co],
    x: _ArrayLikeFloat_co | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[np.float64] | np.float64: ...
@overload
def trapezoid(
    y: _ArrayLike[np.complex128],
    x: _ArrayLikeComplex_co | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[np.complex128] | np.complex128: ...
@overload
def trapezoid(
    y: _ArrayLikeComplex_co,
    x: _ArrayLike[np.complex128],
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[np.complex128] | np.complex128: ...
@overload
def trapezoid(
    y: _ArrayLikeObject_co,
    x: _ArrayLikeObject_co | _ArrayLikeFloat_co | None = None,
    dx: float = 1.0,
    axis: SupportsIndex = -1,
) -> NDArray[np.object_] | Any: ...
@overload
def trapezoid(
    y: _Seq1D[_SupportsRMulFloat[_T]],
    x: _Seq1D[_SupportsRMulFloat[_T] | _T] | None = None,
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> _T: ...
@overload
def trapezoid(
    y: _ArrayLikeComplex_co | _ArrayLike[np.timedelta64 | np.object_],
    x: _ArrayLikeComplex_co | _ArrayLike[np.timedelta64 | np.object_] | None = None,
    dx: complex = 1.0,
    axis: SupportsIndex = -1,
) -> Incomplete: ...

#
@overload  # 0d
def meshgrid(*, copy: bool = True, sparse: bool = False, indexing: _Indexing = "xy") -> tuple[()]: ...
@overload  # 1d, known scalar-type
def meshgrid(
    x1: _ArrayLike[_ScalarT],
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh1[_ScalarT]: ...
@overload  # 1d, unknown scalar-type
def meshgrid(
    x1: ArrayLike,
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh1[Any]: ...
@overload  # 2d, known scalar-types
def meshgrid(
    x1: _ArrayLike[_ScalarT],
    x2: _ArrayLike[_ScalarT1],
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh2[_ScalarT, _ScalarT1]: ...
@overload  # 2d, known/unknown scalar-types
def meshgrid(
    x1: _ArrayLike[_ScalarT],
    x2: ArrayLike,
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh2[_ScalarT, Any]: ...
@overload  # 2d, unknown/known scalar-types
def meshgrid(
    x1: ArrayLike,
    x2: _ArrayLike[_ScalarT],
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh2[Any, _ScalarT]: ...
@overload  # 2d, unknown scalar-types
def meshgrid(
    x1: ArrayLike,
    x2: ArrayLike,
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh2[Any, Any]: ...
@overload  # 3d, known scalar-types
def meshgrid(
    x1: _ArrayLike[_ScalarT],
    x2: _ArrayLike[_ScalarT1],
    x3: _ArrayLike[_ScalarT2],
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh3[_ScalarT, _ScalarT1, _ScalarT2]: ...
@overload  # 3d, unknown scalar-types
def meshgrid(
    x1: ArrayLike,
    x2: ArrayLike,
    x3: ArrayLike,
    /,
    *,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> _Mesh3[Any, Any, Any]: ...
@overload  # ?d, known scalar-types
def meshgrid(
    *xi: _ArrayLike[_ScalarT],
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> tuple[NDArray[_ScalarT], ...]: ...
@overload  # ?d, unknown scalar-types
def meshgrid(
    *xi: ArrayLike,
    copy: bool = True,
    sparse: bool = False,
    indexing: _Indexing = "xy",
) -> tuple[NDArray[Any], ...]: ...

#
def place(arr: np.ndarray, mask: ConvertibleToInt | Sequence[ConvertibleToInt], vals: ArrayLike) -> None: ...

# keep in sync with `insert`
@overload  # known scalar-type, axis=None (default)
def delete(arr: _ArrayLike[_ScalarT], obj: _IndexLike, axis: None = None) -> _Array1D[_ScalarT]: ...
@overload  # known array-type, axis specified
def delete(arr: _ArrayT, obj: _IndexLike, axis: SupportsIndex) -> _ArrayT: ...
@overload  # known scalar-type, axis specified
def delete(arr: _ArrayLike[_ScalarT], obj: _IndexLike, axis: SupportsIndex) -> NDArray[_ScalarT]: ...
@overload  # known scalar-type, axis=None (default)
def delete(arr: ArrayLike, obj: _IndexLike, axis: None = None) -> _Array1D[Any]: ...
@overload  # unknown scalar-type, axis specified
def delete(arr: ArrayLike, obj: _IndexLike, axis: SupportsIndex) -> NDArray[Any]: ...

# keep in sync with `delete`
@overload  # known scalar-type, axis=None (default)
def insert(arr: _ArrayLike[_ScalarT], obj: _IndexLike, values: ArrayLike, axis: None = None) -> _Array1D[_ScalarT]: ...
@overload  # known array-type, axis specified
def insert(arr: _ArrayT, obj: _IndexLike, values: ArrayLike, axis: SupportsIndex) -> _ArrayT: ...
@overload  # known scalar-type, axis specified
def insert(arr: _ArrayLike[_ScalarT], obj: _IndexLike, values: ArrayLike, axis: SupportsIndex) -> NDArray[_ScalarT]: ...
@overload  # known scalar-type, axis=None (default)
def insert(arr: ArrayLike, obj: _IndexLike, values: ArrayLike, axis: None = None) -> _Array1D[Any]: ...
@overload  # unknown scalar-type, axis specified
def insert(arr: ArrayLike, obj: _IndexLike, values: ArrayLike, axis: SupportsIndex) -> NDArray[Any]: ...

#
@overload  # known array type, axis specified
def append(arr: _ArrayT, values: _ArrayT, axis: SupportsIndex) -> _ArrayT: ...
@overload  # 1d, known scalar type, axis specified
def append(arr: _Seq1D[_ScalarT], values: _Seq1D[_ScalarT], axis: SupportsIndex) -> _Array1D[_ScalarT]: ...
@overload  # 2d, known scalar type, axis specified
def append(arr: _Seq2D[_ScalarT], values: _Seq2D[_ScalarT], axis: SupportsIndex) -> _Array2D[_ScalarT]: ...
@overload  # 3d, known scalar type, axis specified
def append(arr: _Seq3D[_ScalarT], values: _Seq3D[_ScalarT], axis: SupportsIndex) -> _Array3D[_ScalarT]: ...
@overload  # ?d, known scalar type, axis specified
def append(arr: _SeqND[_ScalarT], values: _SeqND[_ScalarT], axis: SupportsIndex) -> NDArray[_ScalarT]: ...
@overload  # ?d, unknown scalar type, axis specified
def append(arr: np.ndarray | _SeqND[_ScalarLike_co], values: _SeqND[_ScalarLike_co], axis: SupportsIndex) -> np.ndarray: ...
@overload  # known scalar type, axis=None
def append(arr: _ArrayLike[_ScalarT], values: _ArrayLike[_ScalarT], axis: None = None) -> _Array1D[_ScalarT]: ...
@overload  # unknown scalar type, axis=None
def append(arr: ArrayLike, values: ArrayLike, axis: None = None) -> _Array1D[Any]: ...

#
@overload
def digitize(
    x: _Array[_ShapeT, np.floating | np.integer], bins: _ArrayLikeFloat_co, right: bool = False
) -> _Array[_ShapeT, np.int_]: ...
@overload
def digitize(x: _FloatLike_co, bins: _ArrayLikeFloat_co, right: bool = False) -> np.int_: ...
@overload
def digitize(x: _Seq1D[_FloatLike_co], bins: _ArrayLikeFloat_co, right: bool = False) -> _Array1D[np.int_]: ...
@overload
def digitize(x: _Seq2D[_FloatLike_co], bins: _ArrayLikeFloat_co, right: bool = False) -> _Array2D[np.int_]: ...
@overload
def digitize(x: _Seq3D[_FloatLike_co], bins: _ArrayLikeFloat_co, right: bool = False) -> _Array3D[np.int_]: ...
@overload
def digitize(x: _ArrayLikeFloat_co, bins: _ArrayLikeFloat_co, right: bool = False) -> NDArray[np.int_] | Any: ...
