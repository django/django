from collections.abc import Iterable
from typing import Any, Literal, TypeAlias, TypeVar, overload

from numpy._typing import DTypeLike, NDArray, _SupportsArrayFunc

__all__ = ["require"]

_ArrayT = TypeVar("_ArrayT", bound=NDArray[Any])

_Requirements: TypeAlias = Literal[
    "C", "C_CONTIGUOUS", "CONTIGUOUS",
    "F", "F_CONTIGUOUS", "FORTRAN",
    "A", "ALIGNED",
    "W", "WRITEABLE",
    "O", "OWNDATA"
]
_E: TypeAlias = Literal["E", "ENSUREARRAY"]
_RequirementsWithE: TypeAlias = _Requirements | _E

@overload
def require(
    a: _ArrayT,
    dtype: None = None,
    requirements: _Requirements | Iterable[_Requirements] | None = None,
    *,
    like: _SupportsArrayFunc | None = None
) -> _ArrayT: ...
@overload
def require(
    a: object,
    dtype: DTypeLike | None = None,
    requirements: _E | Iterable[_RequirementsWithE] | None = None,
    *,
    like: _SupportsArrayFunc | None = None
) -> NDArray[Any]: ...
@overload
def require(
    a: object,
    dtype: DTypeLike | None = None,
    requirements: _Requirements | Iterable[_Requirements] | None = None,
    *,
    like: _SupportsArrayFunc | None = None
) -> NDArray[Any]: ...
