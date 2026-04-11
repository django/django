from typing import Any, ClassVar, Final, overload

import numpy as np
import numpy.typing as npt
from numpy._typing import (
    _ArrayLikeFloat_co,
    _ArrayLikeNumber_co,
    _FloatLike_co,
    _NumberLike_co,
)

from ._polybase import ABCPolyBase
from ._polytypes import (
    _Array1,
    _Array2,
    _ArrayLikeCoef_co,
    _FuncBinOp,
    _FuncCompanion,
    _FuncDer,
    _FuncFit,
    _FuncFromRoots,
    _FuncInteg,
    _FuncLine,
    _FuncPow,
    _FuncRoots,
    _FuncUnOp,
    _FuncVal,
    _FuncVal2D,
    _FuncVal3D,
    _FuncVander,
    _FuncVander2D,
    _FuncVander3D,
)
from .polyutils import trimcoef as polytrim

__all__ = [
    "polyzero",
    "polyone",
    "polyx",
    "polydomain",
    "polyline",
    "polyadd",
    "polysub",
    "polymulx",
    "polymul",
    "polydiv",
    "polypow",
    "polyval",
    "polyvalfromroots",
    "polyder",
    "polyint",
    "polyfromroots",
    "polyvander",
    "polyfit",
    "polytrim",
    "polyroots",
    "Polynomial",
    "polyval2d",
    "polyval3d",
    "polygrid2d",
    "polygrid3d",
    "polyvander2d",
    "polyvander3d",
    "polycompanion",
]

polydomain: Final[_Array2[np.float64]] = ...
polyzero: Final[_Array1[np.int_]] = ...
polyone: Final[_Array1[np.int_]] = ...
polyx: Final[_Array2[np.int_]] = ...

polyline: Final[_FuncLine] = ...
polyfromroots: Final[_FuncFromRoots] = ...
polyadd: Final[_FuncBinOp] = ...
polysub: Final[_FuncBinOp] = ...
polymulx: Final[_FuncUnOp] = ...
polymul: Final[_FuncBinOp] = ...
polydiv: Final[_FuncBinOp] = ...
polypow: Final[_FuncPow] = ...
polyder: Final[_FuncDer] = ...
polyint: Final[_FuncInteg] = ...
polyval: Final[_FuncVal] = ...
polyval2d: Final[_FuncVal2D] = ...
polyval3d: Final[_FuncVal3D] = ...

@overload
def polyvalfromroots(x: _FloatLike_co, r: _FloatLike_co, tensor: bool = True) -> np.float64 | Any: ...
@overload
def polyvalfromroots(x: _NumberLike_co, r: _NumberLike_co, tensor: bool = True) -> np.complex128 | Any: ...
@overload
def polyvalfromroots(x: _ArrayLikeFloat_co, r: _ArrayLikeFloat_co, tensor: bool = True) -> npt.NDArray[np.float64 | Any]: ...
@overload
def polyvalfromroots(x: _ArrayLikeNumber_co, r: _ArrayLikeNumber_co, tensor: bool = True) -> npt.NDArray[np.complex128 | Any]: ...
@overload
def polyvalfromroots(x: _ArrayLikeCoef_co, r: _ArrayLikeCoef_co, tensor: bool = True) -> npt.NDArray[np.object_ | Any]: ...

polygrid2d: Final[_FuncVal2D] = ...
polygrid3d: Final[_FuncVal3D] = ...
polyvander: Final[_FuncVander] = ...
polyvander2d: Final[_FuncVander2D] = ...
polyvander3d: Final[_FuncVander3D] = ...
polyfit: Final[_FuncFit] = ...
polycompanion: Final[_FuncCompanion] = ...
polyroots: Final[_FuncRoots] = ...

class Polynomial(ABCPolyBase[None]):
    basis_name: ClassVar[None] = None  # pyright: ignore[reportIncompatibleMethodOverride]
    domain: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
    window: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
