import abc
import decimal
from collections.abc import Iterator, Sequence
from typing import (
    Any,
    ClassVar,
    Generic,
    Literal,
    Self,
    SupportsIndex,
    TypeAlias,
    overload,
)
from typing_extensions import TypeIs, TypeVar

import numpy as np
import numpy.typing as npt
from numpy._typing import (
    _ArrayLikeComplex_co,
    _ArrayLikeFloat_co,
    _FloatLike_co,
    _NumberLike_co,
)

from ._polytypes import (
    _AnyInt,
    _Array2,
    _ArrayLikeCoef_co,
    _ArrayLikeCoefObject_co,
    _CoefLike_co,
    _CoefSeries,
    _Series,
    _SeriesLikeCoef_co,
    _SeriesLikeInt_co,
    _Tuple2,
)

__all__ = ["ABCPolyBase"]

_NameT_co = TypeVar("_NameT_co", bound=str | None, default=str | None, covariant=True)
_PolyT = TypeVar("_PolyT", bound=ABCPolyBase)
_AnyOther: TypeAlias = ABCPolyBase | _CoefLike_co | _SeriesLikeCoef_co

class ABCPolyBase(Generic[_NameT_co], abc.ABC):
    __hash__: ClassVar[None] = None  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleMethodOverride]
    __array_ufunc__: ClassVar[None] = None
    maxpower: ClassVar[Literal[100]] = 100

    _superscript_mapping: ClassVar[dict[int, str]] = ...
    _subscript_mapping: ClassVar[dict[int, str]] = ...
    _use_unicode: ClassVar[bool] = ...

    _symbol: str
    @property
    def symbol(self, /) -> str: ...
    @property
    @abc.abstractmethod
    def domain(self) -> _Array2[np.float64 | Any]: ...
    @property
    @abc.abstractmethod
    def window(self) -> _Array2[np.float64 | Any]: ...
    @property
    @abc.abstractmethod
    def basis_name(self) -> _NameT_co: ...

    coef: _CoefSeries

    def __init__(
        self,
        /,
        coef: _SeriesLikeCoef_co,
        domain: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> None: ...

    #
    @overload
    def __call__(self, /, arg: _PolyT) -> _PolyT: ...
    @overload
    def __call__(self, /, arg: _FloatLike_co | decimal.Decimal) -> np.float64 | Any: ...
    @overload
    def __call__(self, /, arg: _NumberLike_co) -> np.complex128 | Any: ...
    @overload
    def __call__(self, /, arg: _ArrayLikeFloat_co) -> npt.NDArray[np.float64 | Any]: ...
    @overload
    def __call__(self, /, arg: _ArrayLikeComplex_co) -> npt.NDArray[np.complex128 | Any]: ...
    @overload
    def __call__(self, /, arg: _ArrayLikeCoefObject_co) -> npt.NDArray[np.object_]: ...

    # unary ops
    def __neg__(self, /) -> Self: ...
    def __pos__(self, /) -> Self: ...

    # binary ops
    def __add__(self, x: _AnyOther, /) -> Self: ...
    def __sub__(self, x: _AnyOther, /) -> Self: ...
    def __mul__(self, x: _AnyOther, /) -> Self: ...
    def __pow__(self, x: _AnyOther, /) -> Self: ...
    def __truediv__(self, x: _AnyOther, /) -> Self: ...
    def __floordiv__(self, x: _AnyOther, /) -> Self: ...
    def __mod__(self, x: _AnyOther, /) -> Self: ...
    def __divmod__(self, x: _AnyOther, /) -> _Tuple2[Self]: ...

    # reflected binary ops
    def __radd__(self, x: _AnyOther, /) -> Self: ...
    def __rsub__(self, x: _AnyOther, /) -> Self: ...
    def __rmul__(self, x: _AnyOther, /) -> Self: ...
    def __rtruediv__(self, x: _AnyOther, /) -> Self: ...
    def __rfloordiv__(self, x: _AnyOther, /) -> Self: ...
    def __rmod__(self, x: _AnyOther, /) -> Self: ...
    def __rdivmod__(self, x: _AnyOther, /) -> _Tuple2[Self]: ...

    # iterable and sized
    def __len__(self, /) -> int: ...
    def __iter__(self, /) -> Iterator[np.float64 | Any]: ...

    # pickling
    def __getstate__(self, /) -> dict[str, Any]: ...
    def __setstate__(self, dict: dict[str, Any], /) -> None: ...

    #
    def has_samecoef(self, /, other: ABCPolyBase) -> bool: ...
    def has_samedomain(self, /, other: ABCPolyBase) -> bool: ...
    def has_samewindow(self, /, other: ABCPolyBase) -> bool: ...
    def has_sametype(self, /, other: object) -> TypeIs[Self]: ...

    #
    def copy(self, /) -> Self: ...
    def degree(self, /) -> int: ...
    def cutdeg(self, /, deg: int) -> Self: ...
    def trim(self, /, tol: _FloatLike_co = 0) -> Self: ...
    def truncate(self, /, size: _AnyInt) -> Self: ...

    #
    @overload
    def convert(
        self,
        /,
        domain: _SeriesLikeCoef_co | None,
        kind: type[_PolyT],
        window: _SeriesLikeCoef_co | None = None,
    ) -> _PolyT: ...
    @overload
    def convert(
        self,
        /,
        domain: _SeriesLikeCoef_co | None = None,
        *,
        kind: type[_PolyT],
        window: _SeriesLikeCoef_co | None = None,
    ) -> _PolyT: ...
    @overload
    def convert(
        self,
        /,
        domain: _SeriesLikeCoef_co | None = None,
        kind: None = None,
        window: _SeriesLikeCoef_co | None = None,
    ) -> Self: ...

    #
    def mapparms(self, /) -> _Tuple2[Any]: ...
    def integ(
        self,
        /,
        m: SupportsIndex = 1,
        k: _CoefLike_co | _SeriesLikeCoef_co = [],
        lbnd: _CoefLike_co | None = None,
    ) -> Self: ...
    def deriv(self, /, m: SupportsIndex = 1) -> Self: ...
    def roots(self, /) -> _CoefSeries: ...
    def linspace(
        self,
        /,
        n: SupportsIndex = 100,
        domain: _SeriesLikeCoef_co | None = None,
    ) -> _Tuple2[_Series[np.float64 | np.complex128]]: ...

    #
    @overload
    @classmethod
    def fit(
        cls,
        x: _SeriesLikeCoef_co,
        y: _SeriesLikeCoef_co,
        deg: int | _SeriesLikeInt_co,
        domain: _SeriesLikeCoef_co | None = None,
        rcond: _FloatLike_co | None = None,
        full: Literal[False] = False,
        w: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> Self: ...
    @overload
    @classmethod
    def fit(
        cls,
        x: _SeriesLikeCoef_co,
        y: _SeriesLikeCoef_co,
        deg: int | _SeriesLikeInt_co,
        domain: _SeriesLikeCoef_co | None = None,
        rcond: _FloatLike_co | None = None,
        *,
        full: Literal[True],
        w: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> tuple[Self, Sequence[np.inexact | np.int32]]: ...
    @overload
    @classmethod
    def fit(
        cls,
        x: _SeriesLikeCoef_co,
        y: _SeriesLikeCoef_co,
        deg: int | _SeriesLikeInt_co,
        domain: _SeriesLikeCoef_co | None,
        rcond: _FloatLike_co,
        full: Literal[True],
        /,
        w: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> tuple[Self, Sequence[np.inexact | np.int32]]: ...

    #
    @classmethod
    def fromroots(
        cls,
        roots: _ArrayLikeCoef_co,
        domain: _SeriesLikeCoef_co | None = [],
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> Self: ...
    @classmethod
    def identity(
        cls,
        domain: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> Self: ...
    @classmethod
    def basis(
        cls,
        deg: _AnyInt,
        domain: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
        symbol: str = "x",
    ) -> Self: ...
    @classmethod
    def cast(
        cls,
        series: ABCPolyBase,
        domain: _SeriesLikeCoef_co | None = None,
        window: _SeriesLikeCoef_co | None = None,
    ) -> Self: ...
    @classmethod
    def _str_term_unicode(cls, /, i: str, arg_str: str) -> str: ...
    @classmethod
    def _str_term_ascii(cls, /, i: str, arg_str: str) -> str: ...
    @classmethod
    def _repr_latex_term(cls, /, i: str, arg_str: str, needs_parens: bool) -> str: ...
