from _typeshed import ConvertibleToInt
from collections.abc import Callable, Iterable
from typing import (
    Any,
    ClassVar,
    Concatenate,
    Final,
    Literal as L,
    Self,
    TypeVar,
    overload,
)

import numpy as np
import numpy.typing as npt
from numpy._typing import _IntLike_co

from ._polybase import ABCPolyBase
from ._polytypes import (
    _Array1,
    _Array2,
    _CoefSeries,
    _FuncBinOp,
    _FuncCompanion,
    _FuncDer,
    _FuncFit,
    _FuncFromRoots,
    _FuncGauss,
    _FuncInteg,
    _FuncLine,
    _FuncPoly2Ortho,
    _FuncPow,
    _FuncRoots,
    _FuncUnOp,
    _FuncVal,
    _FuncVal2D,
    _FuncVal3D,
    _FuncVander,
    _FuncVander2D,
    _FuncVander3D,
    _FuncWeight,
    _Series,
    _SeriesLikeCoef_co,
)
from .polyutils import trimcoef as chebtrim

__all__ = [
    "chebzero",
    "chebone",
    "chebx",
    "chebdomain",
    "chebline",
    "chebadd",
    "chebsub",
    "chebmulx",
    "chebmul",
    "chebdiv",
    "chebpow",
    "chebval",
    "chebder",
    "chebint",
    "cheb2poly",
    "poly2cheb",
    "chebfromroots",
    "chebvander",
    "chebfit",
    "chebtrim",
    "chebroots",
    "chebpts1",
    "chebpts2",
    "Chebyshev",
    "chebval2d",
    "chebval3d",
    "chebgrid2d",
    "chebgrid3d",
    "chebvander2d",
    "chebvander3d",
    "chebcompanion",
    "chebgauss",
    "chebweight",
    "chebinterpolate",
]

_NumberOrObjectT = TypeVar("_NumberOrObjectT", bound=np.number | np.object_)
_CoefScalarT = TypeVar("_CoefScalarT", bound=np.number | np.bool | np.object_)

def _cseries_to_zseries(c: npt.NDArray[_NumberOrObjectT]) -> _Series[_NumberOrObjectT]: ...
def _zseries_to_cseries(zs: npt.NDArray[_NumberOrObjectT]) -> _Series[_NumberOrObjectT]: ...
def _zseries_mul(z1: npt.NDArray[_NumberOrObjectT], z2: npt.NDArray[_NumberOrObjectT]) -> _Series[_NumberOrObjectT]: ...
def _zseries_div(z1: npt.NDArray[_NumberOrObjectT], z2: npt.NDArray[_NumberOrObjectT]) -> _Series[_NumberOrObjectT]: ...
def _zseries_der(zs: npt.NDArray[_NumberOrObjectT]) -> _Series[_NumberOrObjectT]: ...
def _zseries_int(zs: npt.NDArray[_NumberOrObjectT]) -> _Series[_NumberOrObjectT]: ...

poly2cheb: Final[_FuncPoly2Ortho] = ...
cheb2poly: Final[_FuncUnOp] = ...

chebdomain: Final[_Array2[np.float64]] = ...
chebzero: Final[_Array1[np.int_]] = ...
chebone: Final[_Array1[np.int_]] = ...
chebx: Final[_Array2[np.int_]] = ...

chebline: Final[_FuncLine] = ...
chebfromroots: Final[_FuncFromRoots] = ...
chebadd: Final[_FuncBinOp] = ...
chebsub: Final[_FuncBinOp] = ...
chebmulx: Final[_FuncUnOp] = ...
chebmul: Final[_FuncBinOp] = ...
chebdiv: Final[_FuncBinOp] = ...
chebpow: Final[_FuncPow] = ...
chebder: Final[_FuncDer] = ...
chebint: Final[_FuncInteg] = ...
chebval: Final[_FuncVal] = ...
chebval2d: Final[_FuncVal2D] = ...
chebval3d: Final[_FuncVal3D] = ...
chebgrid2d: Final[_FuncVal2D] = ...
chebgrid3d: Final[_FuncVal3D] = ...
chebvander: Final[_FuncVander] = ...
chebvander2d: Final[_FuncVander2D] = ...
chebvander3d: Final[_FuncVander3D] = ...
chebfit: Final[_FuncFit] = ...
chebcompanion: Final[_FuncCompanion] = ...
chebroots: Final[_FuncRoots] = ...
chebgauss: Final[_FuncGauss] = ...
chebweight: Final[_FuncWeight] = ...
def chebpts1(npts: ConvertibleToInt) -> np.ndarray[tuple[int], np.dtype[np.float64]]: ...
def chebpts2(npts: ConvertibleToInt) -> np.ndarray[tuple[int], np.dtype[np.float64]]: ...

# keep in sync with `Chebyshev.interpolate` (minus `domain` parameter)
@overload
def chebinterpolate(
    func: np.ufunc,
    deg: _IntLike_co,
    args: tuple[()] = (),
) -> npt.NDArray[np.float64 | np.complex128 | np.object_]: ...
@overload
def chebinterpolate(
    func: Callable[[npt.NDArray[np.float64]], _CoefScalarT],
    deg: _IntLike_co,
    args: tuple[()] = (),
) -> npt.NDArray[_CoefScalarT]: ...
@overload
def chebinterpolate(
    func: Callable[Concatenate[npt.NDArray[np.float64], ...], _CoefScalarT],
    deg: _IntLike_co,
    args: Iterable[Any],
) -> npt.NDArray[_CoefScalarT]: ...

class Chebyshev(ABCPolyBase[L["T"]]):
    basis_name: ClassVar[L["T"]] = "T"  # pyright: ignore[reportIncompatibleMethodOverride]
    domain: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
    window: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]

    @overload
    @classmethod
    def interpolate(
        cls,
        func: Callable[[npt.NDArray[np.float64]], _CoefSeries],
        deg: _IntLike_co,
        domain: _SeriesLikeCoef_co | None = None,
        args: tuple[()] = (),
    ) -> Self: ...
    @overload
    @classmethod
    def interpolate(
        cls,
        func: Callable[Concatenate[npt.NDArray[np.float64], ...], _CoefSeries],
        deg: _IntLike_co,
        domain: _SeriesLikeCoef_co | None = None,
        *,
        args: Iterable[Any],
    ) -> Self: ...
    @overload
    @classmethod
    def interpolate(
        cls,
        func: Callable[Concatenate[npt.NDArray[np.float64], ...], _CoefSeries],
        deg: _IntLike_co,
        domain: _SeriesLikeCoef_co | None,
        args: Iterable[Any],
    ) -> Self: ...
