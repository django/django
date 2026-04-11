from _typeshed import Incomplete
from collections.abc import Callable, Sequence
from typing import (
    Any,
    Literal as L,
    Never,
    Protocol,
    TypeAlias,
    TypeVar,
    overload,
    type_check_only,
)

import numpy as np
from numpy import _OrderCF
from numpy._typing import (
    ArrayLike,
    DTypeLike,
    NDArray,
    _ArrayLike,
    _DTypeLike,
    _NumberLike_co,
    _ScalarLike_co,
    _SupportsArray,
    _SupportsArrayFunc,
)

__all__ = [
    "diag",
    "diagflat",
    "eye",
    "fliplr",
    "flipud",
    "tri",
    "triu",
    "tril",
    "vander",
    "histogram2d",
    "mask_indices",
    "tril_indices",
    "tril_indices_from",
    "triu_indices",
    "triu_indices_from",
]

###

_T = TypeVar("_T")
_ArrayT = TypeVar("_ArrayT", bound=np.ndarray)
_ScalarT = TypeVar("_ScalarT", bound=np.generic)
_ComplexT = TypeVar("_ComplexT", bound=np.complexfloating)
_InexactT = TypeVar("_InexactT", bound=np.inexact)
_NumberT = TypeVar("_NumberT", bound=np.number)
_NumberObjectT = TypeVar("_NumberObjectT", bound=np.number | np.object_)
_NumberCoT = TypeVar("_NumberCoT", bound=_Number_co)

_Int_co: TypeAlias = np.integer | np.bool
_Float_co: TypeAlias = np.floating | _Int_co
_Number_co: TypeAlias = np.number | np.bool

_Array1D: TypeAlias = np.ndarray[tuple[int], np.dtype[_ScalarT]]
_Array2D: TypeAlias = np.ndarray[tuple[int, int], np.dtype[_ScalarT]]
# Workaround for mypy's and pyright's lack of compliance with the typing spec for
# overloads for gradual types. This works because only `Any` and `Never` are assignable
# to `Never`.
_ArrayNoD: TypeAlias = np.ndarray[tuple[Never] | tuple[Never, Never], np.dtype[_ScalarT]]

_ArrayLike1D: TypeAlias = _SupportsArray[np.dtype[_ScalarT]] | Sequence[_ScalarT]
_ArrayLike1DInt_co: TypeAlias = _SupportsArray[np.dtype[_Int_co]] | Sequence[int | _Int_co]
_ArrayLike1DFloat_co: TypeAlias = _SupportsArray[np.dtype[_Float_co]] | Sequence[float | _Float_co]
_ArrayLike2DFloat_co: TypeAlias = _SupportsArray[np.dtype[_Float_co]] | Sequence[_ArrayLike1DFloat_co]
_ArrayLike1DNumber_co: TypeAlias = _SupportsArray[np.dtype[_Number_co]] | Sequence[complex | _Number_co]

# The returned arrays dtype must be compatible with `np.equal`
_MaskFunc: TypeAlias = Callable[[NDArray[np.int_], _T], NDArray[_Number_co | np.timedelta64 | np.datetime64 | np.object_]]

_Indices2D: TypeAlias = tuple[_Array1D[np.intp], _Array1D[np.intp]]
_Histogram2D: TypeAlias = tuple[_Array2D[np.float64], _Array1D[_ScalarT], _Array1D[_ScalarT]]

@type_check_only
class _HasShapeAndNDim(Protocol):
    @property  # TODO: require 2d shape once shape-typing has matured
    def shape(self) -> tuple[int, ...]: ...
    @property
    def ndim(self) -> int: ...

###

# keep in sync with `flipud`
@overload
def fliplr(m: _ArrayT) -> _ArrayT: ...
@overload
def fliplr(m: _ArrayLike[_ScalarT]) -> NDArray[_ScalarT]: ...
@overload
def fliplr(m: ArrayLike) -> NDArray[Any]: ...

# keep in sync with `fliplr`
@overload
def flipud(m: _ArrayT) -> _ArrayT: ...
@overload
def flipud(m: _ArrayLike[_ScalarT]) -> NDArray[_ScalarT]: ...
@overload
def flipud(m: ArrayLike) -> NDArray[Any]: ...

#
@overload
def eye(
    N: int,
    M: int | None = None,
    k: int = 0,
    dtype: None = ...,  # = float  # stubdefaulter: ignore[missing-default]
    order: _OrderCF = "C",
    *,
    device: L["cpu"] | None = None,
    like: _SupportsArrayFunc | None = None,
) -> _Array2D[np.float64]: ...
@overload
def eye(
    N: int,
    M: int | None,
    k: int,
    dtype: _DTypeLike[_ScalarT],
    order: _OrderCF = "C",
    *,
    device: L["cpu"] | None = None,
    like: _SupportsArrayFunc | None = None,
) -> _Array2D[_ScalarT]: ...
@overload
def eye(
    N: int,
    M: int | None = None,
    k: int = 0,
    *,
    dtype: _DTypeLike[_ScalarT],
    order: _OrderCF = "C",
    device: L["cpu"] | None = None,
    like: _SupportsArrayFunc | None = None,
) -> _Array2D[_ScalarT]: ...
@overload
def eye(
    N: int,
    M: int | None = None,
    k: int = 0,
    dtype: DTypeLike | None = ...,  # = float
    order: _OrderCF = "C",
    *,
    device: L["cpu"] | None = None,
    like: _SupportsArrayFunc | None = None,
) -> _Array2D[Incomplete]: ...

#
@overload
def diag(v: _ArrayNoD[_ScalarT] | Sequence[Sequence[_ScalarT]], k: int = 0) -> NDArray[_ScalarT]: ...
@overload
def diag(v: _Array2D[_ScalarT] | Sequence[Sequence[_ScalarT]], k: int = 0) -> _Array1D[_ScalarT]: ...
@overload
def diag(v: _Array1D[_ScalarT] | Sequence[_ScalarT], k: int = 0) -> _Array2D[_ScalarT]: ...
@overload
def diag(v: Sequence[Sequence[_ScalarLike_co]], k: int = 0) -> _Array1D[Incomplete]: ...
@overload
def diag(v: Sequence[_ScalarLike_co], k: int = 0) -> _Array2D[Incomplete]: ...
@overload
def diag(v: _ArrayLike[_ScalarT], k: int = 0) -> NDArray[_ScalarT]: ...
@overload
def diag(v: ArrayLike, k: int = 0) -> NDArray[Incomplete]: ...

# keep in sync with `numpy.ma.extras.diagflat`
@overload
def diagflat(v: _ArrayLike[_ScalarT], k: int = 0) -> _Array2D[_ScalarT]: ...
@overload
def diagflat(v: ArrayLike, k: int = 0) -> _Array2D[Incomplete]: ...

#
@overload
def tri(
    N: int,
    M: int | None = None,
    k: int = 0,
    dtype: None = ...,  # = float  # stubdefaulter: ignore[missing-default]
    *,
    like: _SupportsArrayFunc | None = None
) -> _Array2D[np.float64]: ...
@overload
def tri(
    N: int,
    M: int | None,
    k: int,
    dtype: _DTypeLike[_ScalarT],
    *,
    like: _SupportsArrayFunc | None = None
) -> _Array2D[_ScalarT]: ...
@overload
def tri(
    N: int,
    M: int | None = None,
    k: int = 0,
    *,
    dtype: _DTypeLike[_ScalarT],
    like: _SupportsArrayFunc | None = None
) -> _Array2D[_ScalarT]: ...
@overload
def tri(
    N: int,
    M: int | None = None,
    k: int = 0,
    dtype: DTypeLike | None = ...,  # = float
    *,
    like: _SupportsArrayFunc | None = None
) -> _Array2D[Any]: ...

# keep in sync with `triu`
@overload
def tril(m: _ArrayT, k: int = 0) -> _ArrayT: ...
@overload
def tril(m: _ArrayLike[_ScalarT], k: int = 0) -> NDArray[_ScalarT]: ...
@overload
def tril(m: ArrayLike, k: int = 0) -> NDArray[Any]: ...

# keep in sync with `tril`
@overload
def triu(m: _ArrayT, k: int = 0) -> _ArrayT: ...
@overload
def triu(m: _ArrayLike[_ScalarT], k: int = 0) -> NDArray[_ScalarT]: ...
@overload
def triu(m: ArrayLike, k: int = 0) -> NDArray[Any]: ...

# we use `list` (invariant) instead of `Sequence` (covariant) to avoid overlap
@overload
def vander(x: _ArrayLike1D[_NumberObjectT], N: int | None = None, increasing: bool = False) -> _Array2D[_NumberObjectT]: ...
@overload
def vander(x: _ArrayLike1D[np.bool] | list[int], N: int | None = None, increasing: bool = False) -> _Array2D[np.int_]: ...
@overload
def vander(x: list[float], N: int | None = None, increasing: bool = False) -> _Array2D[np.float64]: ...
@overload
def vander(x: list[complex], N: int | None = None, increasing: bool = False) -> _Array2D[np.complex128]: ...
@overload  # fallback
def vander(x: Sequence[_NumberLike_co], N: int | None = None, increasing: bool = False) -> _Array2D[Any]: ...

#
@overload
def histogram2d(
    x: _ArrayLike1D[_ComplexT],
    y: _ArrayLike1D[_ComplexT | _Float_co],
    bins: int | Sequence[int] = 10,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_ComplexT]: ...
@overload
def histogram2d(
    x: _ArrayLike1D[_ComplexT | _Float_co],
    y: _ArrayLike1D[_ComplexT],
    bins: int | Sequence[int] = 10,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_ComplexT]: ...
@overload
def histogram2d(
    x: _ArrayLike1D[_InexactT],
    y: _ArrayLike1D[_InexactT | _Int_co],
    bins: int | Sequence[int] = 10,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_InexactT]: ...
@overload
def histogram2d(
    x: _ArrayLike1D[_InexactT | _Int_co],
    y: _ArrayLike1D[_InexactT],
    bins: int | Sequence[int] = 10,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_InexactT]: ...
@overload
def histogram2d(
    x: _ArrayLike1DInt_co | Sequence[float],
    y: _ArrayLike1DInt_co | Sequence[float],
    bins: int | Sequence[int] = 10,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.float64]: ...
@overload
def histogram2d(
    x: Sequence[complex],
    y: Sequence[complex],
    bins: int | Sequence[int] = 10,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.complex128 | Any]: ...
@overload
def histogram2d(
    x: _ArrayLike1DNumber_co,
    y: _ArrayLike1DNumber_co,
    bins: _ArrayLike1D[_NumberCoT] | Sequence[_ArrayLike1D[_NumberCoT]],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_NumberCoT]: ...
@overload
def histogram2d(
    x: _ArrayLike1D[_InexactT],
    y: _ArrayLike1D[_InexactT],
    bins: Sequence[_ArrayLike1D[_NumberCoT] | int],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_InexactT | _NumberCoT]: ...
@overload
def histogram2d(
    x: _ArrayLike1D[_InexactT],
    y: _ArrayLike1D[_InexactT],
    bins: Sequence[_ArrayLike1DNumber_co | int],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[_InexactT | Any]: ...
@overload
def histogram2d(
    x: _ArrayLike1DInt_co | Sequence[float],
    y: _ArrayLike1DInt_co | Sequence[float],
    bins: Sequence[_ArrayLike1D[_NumberCoT] | int],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.float64 | _NumberCoT]: ...
@overload
def histogram2d(
    x: _ArrayLike1DInt_co | Sequence[float],
    y: _ArrayLike1DInt_co | Sequence[float],
    bins: Sequence[_ArrayLike1DNumber_co | int],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.float64 | Any]: ...
@overload
def histogram2d(
    x: Sequence[complex],
    y: Sequence[complex],
    bins: Sequence[_ArrayLike1D[_NumberCoT] | int],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.complex128 | _NumberCoT]: ...
@overload
def histogram2d(
    x: Sequence[complex],
    y: Sequence[complex],
    bins: Sequence[_ArrayLike1DNumber_co | int],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.complex128 | Any]: ...
@overload
def histogram2d(
    x: _ArrayLike1DNumber_co,
    y: _ArrayLike1DNumber_co,
    bins: Sequence[Sequence[int]],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.int_]: ...
@overload
def histogram2d(
    x: _ArrayLike1DNumber_co,
    y: _ArrayLike1DNumber_co,
    bins: Sequence[Sequence[float]],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.float64 | Any]: ...
@overload
def histogram2d(
    x: _ArrayLike1DNumber_co,
    y: _ArrayLike1DNumber_co,
    bins: Sequence[Sequence[complex]],
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[np.complex128 | Any]: ...
@overload
def histogram2d(
    x: _ArrayLike1DNumber_co,
    y: _ArrayLike1DNumber_co,
    bins: Sequence[_ArrayLike1DNumber_co | int] | int,
    range: _ArrayLike2DFloat_co | None = None,
    density: bool | None = None,
    weights: _ArrayLike1DFloat_co | None = None,
) -> _Histogram2D[Any]: ...

# NOTE: we're assuming/demanding here the `mask_func` returns
# an ndarray of shape `(n, n)`; otherwise there is the possibility
# of the output tuple having more or less than 2 elements
@overload
def mask_indices(n: int, mask_func: _MaskFunc[int], k: int = 0) -> _Indices2D: ...
@overload
def mask_indices(n: int, mask_func: _MaskFunc[_T], k: _T) -> _Indices2D: ...

#
def tril_indices(n: int, k: int = 0, m: int | None = None) -> _Indices2D: ...
def triu_indices(n: int, k: int = 0, m: int | None = None) -> _Indices2D: ...

# these will accept anything with `shape: tuple[int, int]` and `ndim: int` attributes
def tril_indices_from(arr: _HasShapeAndNDim, k: int = 0) -> _Indices2D: ...
def triu_indices_from(arr: _HasShapeAndNDim, k: int = 0) -> _Indices2D: ...
