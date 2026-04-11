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
from .polyutils import trimcoef as legtrim

__all__ = [
    "legzero",
    "legone",
    "legx",
    "legdomain",
    "legline",
    "legadd",
    "legsub",
    "legmulx",
    "legmul",
    "legdiv",
    "legpow",
    "legval",
    "legder",
    "legint",
    "leg2poly",
    "poly2leg",
    "legfromroots",
    "legvander",
    "legfit",
    "legtrim",
    "legroots",
    "Legendre",
    "legval2d",
    "legval3d",
    "leggrid2d",
    "leggrid3d",
    "legvander2d",
    "legvander3d",
    "legcompanion",
    "leggauss",
    "legweight",
]

poly2leg: Final[_FuncPoly2Ortho] = ...
leg2poly: Final[_FuncUnOp] = ...

legdomain: Final[_Array2[np.float64]] = ...
legzero: Final[_Array1[np.int_]] = ...
legone: Final[_Array1[np.int_]] = ...
legx: Final[_Array2[np.int_]] = ...

legline: Final[_FuncLine] = ...
legfromroots: Final[_FuncFromRoots] = ...
legadd: Final[_FuncBinOp] = ...
legsub: Final[_FuncBinOp] = ...
legmulx: Final[_FuncUnOp] = ...
legmul: Final[_FuncBinOp] = ...
legdiv: Final[_FuncBinOp] = ...
legpow: Final[_FuncPow] = ...
legder: Final[_FuncDer] = ...
legint: Final[_FuncInteg] = ...
legval: Final[_FuncVal] = ...
legval2d: Final[_FuncVal2D] = ...
legval3d: Final[_FuncVal3D] = ...
leggrid2d: Final[_FuncVal2D] = ...
leggrid3d: Final[_FuncVal3D] = ...
legvander: Final[_FuncVander] = ...
legvander2d: Final[_FuncVander2D] = ...
legvander3d: Final[_FuncVander3D] = ...
legfit: Final[_FuncFit] = ...
legcompanion: Final[_FuncCompanion] = ...
legroots: Final[_FuncRoots] = ...
leggauss: Final[_FuncGauss] = ...
legweight: Final[_FuncWeight] = ...

class Legendre(ABCPolyBase[L["P"]]):
    basis_name: ClassVar[L["P"]] = "P"  # pyright: ignore[reportIncompatibleMethodOverride]
    domain: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
    window: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
