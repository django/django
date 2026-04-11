from _typeshed import Incomplete
from collections.abc import Mapping, Sequence
from types import EllipsisType
from typing import Any, ClassVar, Literal as L, Self, SupportsIndex, TypeAlias, overload
from typing_extensions import TypeVar

import numpy as np
from numpy._typing import (
    ArrayLike,
    DTypeLike,
    NDArray,
    _AnyShape,
    _ArrayLikeInt_co,
    _NestedSequence,
    _ShapeLike,
)

__all__ = ["asmatrix", "bmat", "matrix"]

_T = TypeVar("_T")
_ArrayT = TypeVar("_ArrayT", bound=np.ndarray)
_BoolOrIntArrayT = TypeVar("_BoolOrIntArrayT", bound=NDArray[np.integer | np.bool])
_ScalarT = TypeVar("_ScalarT", bound=np.generic)
_ShapeT_co = TypeVar("_ShapeT_co", bound=_2D, default=_2D, covariant=True)
_DTypeT_co = TypeVar("_DTypeT_co", bound=np.dtype, default=np.dtype, covariant=True)

_2D: TypeAlias = tuple[int, int]
_Matrix: TypeAlias = matrix[_2D, np.dtype[_ScalarT]]
_ToIndex1: TypeAlias = slice | EllipsisType | NDArray[np.integer | np.bool] | _NestedSequence[int] | None
_ToIndex2: TypeAlias = tuple[_ToIndex1, _ToIndex1 | SupportsIndex] | tuple[_ToIndex1 | SupportsIndex, _ToIndex1]

class matrix(np.ndarray[_ShapeT_co, _DTypeT_co]):
    __array_priority__: ClassVar[float] = 10.0  # pyright: ignore[reportIncompatibleMethodOverride]

    def __new__(
        subtype,  # pyright: ignore[reportSelfClsParameterName]
        data: ArrayLike,
        dtype: DTypeLike | None = None,
        copy: bool = True,
    ) -> _Matrix[Incomplete]: ...

    #
    @overload  # type: ignore[override]
    def __getitem__(
        self, key: SupportsIndex | _ArrayLikeInt_co | tuple[SupportsIndex | _ArrayLikeInt_co, ...], /
    ) -> Incomplete: ...
    @overload
    def __getitem__(self, key: _ToIndex1 | _ToIndex2, /) -> matrix[_2D, _DTypeT_co]: ...
    @overload
    def __getitem__(self: _Matrix[np.void], key: str, /) -> _Matrix[Incomplete]: ...
    @overload
    def __getitem__(self: _Matrix[np.void], key: list[str], /) -> matrix[_2D, _DTypeT_co]: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    #
    def __mul__(self, other: ArrayLike, /) -> _Matrix[Incomplete]: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
    def __rmul__(self, other: ArrayLike, /) -> _Matrix[Incomplete]: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]

    #
    def __pow__(self, other: ArrayLike, /) -> _Matrix[Incomplete]: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
    def __rpow__(self, other: ArrayLike, /) -> _Matrix[Incomplete]: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `prod` and `mean`
    @overload  # type: ignore[override]
    def sum(self, axis: None = None, dtype: DTypeLike | None = None, out: None = None) -> Incomplete: ...
    @overload
    def sum(self, axis: _ShapeLike, dtype: DTypeLike | None = None, out: None = None) -> _Matrix[Incomplete]: ...
    @overload
    def sum(self, axis: _ShapeLike | None, dtype: DTypeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def sum(self, axis: _ShapeLike | None = None, dtype: DTypeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `sum` and `mean`
    @overload  # type: ignore[override]
    def prod(self, axis: None = None, dtype: DTypeLike | None = None, out: None = None) -> Incomplete: ...
    @overload
    def prod(self, axis: _ShapeLike, dtype: DTypeLike | None = None, out: None = None) -> _Matrix[Incomplete]: ...
    @overload
    def prod(self, axis: _ShapeLike | None, dtype: DTypeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def prod(self, axis: _ShapeLike | None = None, dtype: DTypeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `sum` and `prod`
    @overload  # type: ignore[override]
    def mean(self, axis: None = None, dtype: DTypeLike | None = None, out: None = None) -> Incomplete: ...
    @overload
    def mean(self, axis: _ShapeLike, dtype: DTypeLike | None = None, out: None = None) -> _Matrix[Incomplete]: ...
    @overload
    def mean(self, axis: _ShapeLike | None, dtype: DTypeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def mean(self, axis: _ShapeLike | None = None, dtype: DTypeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `var`
    @overload  # type: ignore[override]
    def std(self, axis: None = None, dtype: DTypeLike | None = None, out: None = None, ddof: float = 0) -> Incomplete: ...
    @overload
    def std(self, axis: _ShapeLike, dtype: DTypeLike | None = None, out: None = None, ddof: float = 0) -> _Matrix[Incomplete]: ...
    @overload
    def std(self, axis: _ShapeLike | None, dtype: DTypeLike | None, out: _ArrayT, ddof: float = 0) -> _ArrayT: ...
    @overload
    def std(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, axis: _ShapeLike | None = None, dtype: DTypeLike | None = None, *, out: _ArrayT, ddof: float = 0
    ) -> _ArrayT: ...

    # keep in sync with `std`
    @overload  # type: ignore[override]
    def var(self, axis: None = None, dtype: DTypeLike | None = None, out: None = None, ddof: float = 0) -> Incomplete: ...
    @overload
    def var(self, axis: _ShapeLike, dtype: DTypeLike | None = None, out: None = None, ddof: float = 0) -> _Matrix[Incomplete]: ...
    @overload
    def var(self, axis: _ShapeLike | None, dtype: DTypeLike | None, out: _ArrayT, ddof: float = 0) -> _ArrayT: ...
    @overload
    def var(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, axis: _ShapeLike | None = None, dtype: DTypeLike | None = None, *, out: _ArrayT, ddof: float = 0
    ) -> _ArrayT: ...

    # keep in sync with `all`
    @overload  # type: ignore[override]
    def any(self, axis: None = None, out: None = None) -> np.bool: ...
    @overload
    def any(self, axis: _ShapeLike, out: None = None) -> _Matrix[np.bool]: ...
    @overload
    def any(self, axis: _ShapeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def any(self, axis: _ShapeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `any`
    @overload  # type: ignore[override]
    def all(self, axis: None = None, out: None = None) -> np.bool: ...
    @overload
    def all(self, axis: _ShapeLike, out: None = None) -> _Matrix[np.bool]: ...
    @overload
    def all(self, axis: _ShapeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def all(self, axis: _ShapeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `min` and `ptp`
    @overload  # type: ignore[override]
    def max(self: NDArray[_ScalarT], axis: None = None, out: None = None) -> _ScalarT: ...
    @overload
    def max(self, axis: _ShapeLike, out: None = None) -> matrix[_2D, _DTypeT_co]: ...
    @overload
    def max(self, axis: _ShapeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def max(self, axis: _ShapeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `max` and `ptp`
    @overload  # type: ignore[override]
    def min(self: NDArray[_ScalarT], axis: None = None, out: None = None) -> _ScalarT: ...
    @overload
    def min(self, axis: _ShapeLike, out: None = None) -> matrix[_2D, _DTypeT_co]: ...
    @overload
    def min(self, axis: _ShapeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def min(self, axis: _ShapeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `max` and `min`
    @overload
    def ptp(self: NDArray[_ScalarT], axis: None = None, out: None = None) -> _ScalarT: ...
    @overload
    def ptp(self, axis: _ShapeLike, out: None = None) -> matrix[_2D, _DTypeT_co]: ...
    @overload
    def ptp(self, axis: _ShapeLike | None, out: _ArrayT) -> _ArrayT: ...
    @overload
    def ptp(self, axis: _ShapeLike | None = None, *, out: _ArrayT) -> _ArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `argmin`
    @overload  # type: ignore[override]
    def argmax(self: NDArray[_ScalarT], axis: None = None, out: None = None) -> np.intp: ...
    @overload
    def argmax(self, axis: _ShapeLike, out: None = None) -> _Matrix[np.intp]: ...
    @overload
    def argmax(self, axis: _ShapeLike | None, out: _BoolOrIntArrayT) -> _BoolOrIntArrayT: ...
    @overload
    def argmax(self, axis: _ShapeLike | None = None, *, out: _BoolOrIntArrayT) -> _BoolOrIntArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # keep in sync with `argmax`
    @overload  # type: ignore[override]
    def argmin(self: NDArray[_ScalarT], axis: None = None, out: None = None) -> np.intp: ...
    @overload
    def argmin(self, axis: _ShapeLike, out: None = None) -> _Matrix[np.intp]: ...
    @overload
    def argmin(self, axis: _ShapeLike | None, out: _BoolOrIntArrayT) -> _BoolOrIntArrayT: ...
    @overload
    def argmin(self, axis: _ShapeLike | None = None, *, out: _BoolOrIntArrayT) -> _BoolOrIntArrayT: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # the second overload handles the (rare) case that the matrix is not 2-d
    @overload
    def tolist(self: _Matrix[np.generic[_T]]) -> list[list[_T]]: ...  # pyright: ignore[reportIncompatibleMethodOverride]
    @overload
    def tolist(self) -> Incomplete: ...  # pyright: ignore[reportIncompatibleMethodOverride]

    # these three methods will at least return a `2-d` array of shape (1, n)
    def squeeze(self, /, axis: _ShapeLike | None = None) -> matrix[_2D, _DTypeT_co]: ...
    def ravel(self, /, order: L["K", "A", "C", "F"] | None = "C") -> matrix[_2D, _DTypeT_co]: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
    def flatten(self, /, order: L["K", "A", "C", "F"] | None = "C") -> matrix[_2D, _DTypeT_co]: ...  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]

    # matrix.T is inherited from _ScalarOrArrayCommon
    def getT(self) -> Self: ...
    @property
    def I(self) -> _Matrix[Incomplete]: ...  # noqa: E743
    def getI(self) -> _Matrix[Incomplete]: ...
    @property
    def A(self) -> np.ndarray[_2D, _DTypeT_co]: ...
    def getA(self) -> np.ndarray[_2D, _DTypeT_co]: ...
    @property
    def A1(self) -> np.ndarray[_AnyShape, _DTypeT_co]: ...
    def getA1(self) -> np.ndarray[_AnyShape, _DTypeT_co]: ...
    @property
    def H(self) -> matrix[_2D, _DTypeT_co]: ...
    def getH(self) -> matrix[_2D, _DTypeT_co]: ...

def bmat(
    obj: str | Sequence[ArrayLike] | NDArray[Any],
    ldict: Mapping[str, Any] | None = None,
    gdict: Mapping[str, Any] | None = None,
) -> _Matrix[Incomplete]: ...

def asmatrix(data: ArrayLike, dtype: DTypeLike | None = None) -> _Matrix[Incomplete]: ...
