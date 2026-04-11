from typing import Any, ClassVar, Final, Literal as L

import numpy as np

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
from .polyutils import trimcoef as lagtrim

__all__ = [
    "lagzero",
    "lagone",
    "lagx",
    "lagdomain",
    "lagline",
    "lagadd",
    "lagsub",
    "lagmulx",
    "lagmul",
    "lagdiv",
    "lagpow",
    "lagval",
    "lagder",
    "lagint",
    "lag2poly",
    "poly2lag",
    "lagfromroots",
    "lagvander",
    "lagfit",
    "lagtrim",
    "lagroots",
    "Laguerre",
    "lagval2d",
    "lagval3d",
    "laggrid2d",
    "laggrid3d",
    "lagvander2d",
    "lagvander3d",
    "lagcompanion",
    "laggauss",
    "lagweight",
]

poly2lag: Final[_FuncPoly2Ortho] = ...
lag2poly: Final[_FuncUnOp] = ...

lagdomain: Final[_Array2[np.float64]] = ...
lagzero: Final[_Array1[np.int_]] = ...
lagone: Final[_Array1[np.int_]] = ...
lagx: Final[_Array2[np.int_]] = ...

lagline: Final[_FuncLine] = ...
lagfromroots: Final[_FuncFromRoots] = ...
lagadd: Final[_FuncBinOp] = ...
lagsub: Final[_FuncBinOp] = ...
lagmulx: Final[_FuncUnOp] = ...
lagmul: Final[_FuncBinOp] = ...
lagdiv: Final[_FuncBinOp] = ...
lagpow: Final[_FuncPow] = ...
lagder: Final[_FuncDer] = ...
lagint: Final[_FuncInteg] = ...
lagval: Final[_FuncVal] = ...
lagval2d: Final[_FuncVal2D] = ...
lagval3d: Final[_FuncVal3D] = ...
laggrid2d: Final[_FuncVal2D] = ...
laggrid3d: Final[_FuncVal3D] = ...
lagvander: Final[_FuncVander] = ...
lagvander2d: Final[_FuncVander2D] = ...
lagvander3d: Final[_FuncVander3D] = ...
lagfit: Final[_FuncFit] = ...
lagcompanion: Final[_FuncCompanion] = ...
lagroots: Final[_FuncRoots] = ...
laggauss: Final[_FuncGauss] = ...
lagweight: Final[_FuncWeight] = ...

class Laguerre(ABCPolyBase[L["L"]]):
    basis_name: ClassVar[L["L"]] = "L"  # pyright: ignore[reportIncompatibleMethodOverride]
    domain: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
    window: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
