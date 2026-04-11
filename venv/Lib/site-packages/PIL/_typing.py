from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

TYPE_CHECKING = False
if TYPE_CHECKING:
    from numbers import _IntegralLike as IntegralLike

    try:
        import numpy.typing as npt

        NumpyArray = npt.NDArray[Any]
    except ImportError:
        pass

if sys.version_info >= (3, 13):
    from types import CapsuleType
else:
    CapsuleType = object

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:
    Buffer = Any


_Ink = float | tuple[int, ...] | str

Coords = Sequence[float] | Sequence[Sequence[float]]


_T_co = TypeVar("_T_co", covariant=True)


class SupportsRead(Protocol[_T_co]):
    def read(self, length: int = ..., /) -> _T_co: ...


StrOrBytesPath = str | bytes | os.PathLike[str] | os.PathLike[bytes]


__all__ = ["Buffer", "IntegralLike", "StrOrBytesPath", "SupportsRead"]
