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
from .polyutils import trimcoef as hermtrim

__all__ = [
    "hermzero",
    "hermone",
    "hermx",
    "hermdomain",
    "hermline",
    "hermadd",
    "hermsub",
    "hermmulx",
    "hermmul",
    "hermdiv",
    "hermpow",
    "hermval",
    "hermder",
    "hermint",
    "herm2poly",
    "poly2herm",
    "hermfromroots",
    "hermvander",
    "hermfit",
    "hermtrim",
    "hermroots",
    "Hermite",
    "hermval2d",
    "hermval3d",
    "hermgrid2d",
    "hermgrid3d",
    "hermvander2d",
    "hermvander3d",
    "hermcompanion",
    "hermgauss",
    "hermweight",
]

_ShapeT = TypeVar("_ShapeT", bound=_Shape)

poly2herm: Final[_FuncPoly2Ortho] = ...
herm2poly: Final[_FuncUnOp] = ...

hermdomain: Final[_Array2[np.float64]] = ...
hermzero: Final[_Array1[np.int_]] = ...
hermone: Final[_Array1[np.int_]] = ...
hermx: Final[_Array2[np.int_]] = ...

hermline: Final[_FuncLine] = ...
hermfromroots: Final[_FuncFromRoots] = ...
hermadd: Final[_FuncBinOp] = ...
hermsub: Final[_FuncBinOp] = ...
hermmulx: Final[_FuncUnOp] = ...
hermmul: Final[_FuncBinOp] = ...
hermdiv: Final[_FuncBinOp] = ...
hermpow: Final[_FuncPow] = ...
hermder: Final[_FuncDer] = ...
hermint: Final[_FuncInteg] = ...
hermval: Final[_FuncVal] = ...
hermval2d: Final[_FuncVal2D] = ...
hermval3d: Final[_FuncVal3D] = ...
hermgrid2d: Final[_FuncVal2D] = ...
hermgrid3d: Final[_FuncVal3D] = ...
hermvander: Final[_FuncVander] = ...
hermvander2d: Final[_FuncVander2D] = ...
hermvander3d: Final[_FuncVander3D] = ...
hermfit: Final[_FuncFit] = ...
hermcompanion: Final[_FuncCompanion] = ...
hermroots: Final[_FuncRoots] = ...

def _normed_hermite_n(x: np.ndarray[_ShapeT, np.dtype[np.float64]], n: int) -> np.ndarray[_ShapeT, np.dtype[np.float64]]: ...

hermgauss: Final[_FuncGauss] = ...
hermweight: Final[_FuncWeight] = ...

class Hermite(ABCPolyBase[L["H"]]):
    basis_name: ClassVar[L["H"]] = "H"  # pyright: ignore[reportIncompatibleMethodOverride]
    domain: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
    window: _Array2[np.float64 | Any] = ...  # pyright: ignore[reportIncompatibleMethodOverride]
