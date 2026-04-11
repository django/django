from typing import Any, ClassVar, Final, Literal as L, TypeVar

import numpy as np
from numpy._typing import _Shape

from ._polybase import ABCPolyBase
from ._polytypes import (
    _Array1,
    _Array2,
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
)
from .polyutils import trimcoef as hermetrim

__all__ = [
    "hermezero",
    "hermeone",
    "hermex",
    "hermedomain",
    "hermeline",
    "hermeadd",
    "hermesub",
    "hermemulx",
    "hermemul",
    "hermediv",
    "hermepow",
    "hermeval",
    "hermeder",
    "hermeint",
    "herme2poly",
    "poly2herme",
    "hermefromroots",
    "hermevander",
    "hermefit",
    "hermetrim",
    "hermeroots",
    "HermiteE",
    "hermeval2d",
    "hermeval3d",
    "hermegrid2d",
    "hermegrid3d",
    "hermevander2d",
    "hermevander3d",
    "hermecompanion",
    "hermegauss",
    "hermeweight",
]

_ShapeT = TypeVar("_ShapeT", bound=_Shape)

poly2herme: Final[_FuncPoly2Ortho] = ...
herme2poly: Final[_FuncUnOp] = ...

hermedomain: Final[_Array2[np.float64]] = ...
hermezero: Final[_Array1[np.int_]] = ...
hermeone: Final[_Array1[np.int_]] = ...
hermex: Final[_Array2[np.int_]] = ...

hermeline: Final[_FuncLine] = ...
hermefromroots: Final[_FuncFromRoots] = ...
hermeadd: Final[_FuncBinOp] = ...
hermesub: Final[_FuncBinOp] = ...
hermemulx: Final[_FuncUnOp] = ...
hermemul: Final[_FuncBinOp] = ...
hermediv: Final[_FuncBinOp] = ...
hermepow: Final[_FuncPow] = ...
hermeder: Final[_FuncDer] = ...
hermeint: Final[_FuncInteg] = ...
hermeval: Final[_FuncVal] = ...
hermeval2d: Final[_FuncVal2D] = ...
hermeval3d: Final[_FuncVal3D] = ...
hermegrid2d: Final[_FuncVal2D] = ...
hermegrid3d: Final[_FuncVal3D] = ...
hermevander: Final[_FuncVander] = ...
hermevander2d: Final[_FuncVander2D] = ...
hermevander3d: Final[_FuncVander3D] = ...
hermefit: Final[_FuncFit] = ...
hermecompanion: Final[_FuncCompanion] = ...
hermeroots: Final[_FuncRoots] = ...

def _normed_hermite_e_n(x: np.ndarray[_ShapeT, np.dtype[np.float64]], n: int) -> np.ndarray[_ShapeT, np.dtype[np.float64]]: ...

hermegauss: Final[_FuncGauss] = ...
hermeweight: Final[_FuncWeight] = ...

class HermiteE(ABCPolyBase[L["He"]]):
    basis_name: ClassVar[L["He"]] = "He"  # pyright: ignore[reportIncompatibleMethodOverride]
    domain: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
    window: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
