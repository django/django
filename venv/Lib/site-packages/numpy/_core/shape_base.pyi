from collections.abc import Sequence
from typing import Any, SupportsIndex, TypeVar, overload

from numpy import _CastingKind, generic
from numpy._typing import ArrayLike, DTypeLike, NDArray, _ArrayLike, _DTypeLike

__all__ = [
    "atleast_1d",
    "atleast_2d",
    "atleast_3d",
    "block",
    "hstack",
    "stack",
    "unstack",
    "vstack",
]

_T = TypeVar("_T")
_ScalarT = TypeVar("_ScalarT", bound=generic)
_ScalarT1 = TypeVar("_ScalarT1", bound=generic)
_ScalarT2 = TypeVar("_ScalarT2", bound=generic)
_ArrayT = TypeVar("_ArrayT", bound=NDArray[Any])

###

# keep in sync with `numpy.ma.extras.atleast_1d`
@overload
def atleast_1d(a0: _ArrayLike[_ScalarT], /) -> NDArray[_ScalarT]: ...
@overload
def atleast_1d(a0: _ArrayLike[_ScalarT1], a1: _ArrayLike[_ScalarT2], /) -> tuple[NDArray[_ScalarT1], NDArray[_ScalarT2]]: ...
@overload
def atleast_1d(a0: _ArrayLike[_ScalarT], a1: _ArrayLike[_ScalarT], /, *arys: _ArrayLike[_ScalarT]) -> tuple[NDArray[_ScalarT], ...]: ...
@overload
def atleast_1d(a0: ArrayLike, /) -> NDArray[Any]: ...
@overload
def atleast_1d(a0: ArrayLike, a1: ArrayLike, /) -> tuple[NDArray[Any], NDArray[Any]]: ...
@overload
def atleast_1d(a0: ArrayLike, a1: ArrayLike, /, *ai: ArrayLike) -> tuple[NDArray[Any], ...]: ...

# keep in sync with `numpy.ma.extras.atleast_2d`
@overload
def atleast_2d(a0: _ArrayLike[_ScalarT], /) -> NDArray[_ScalarT]: ...
@overload
def atleast_2d(a0: _ArrayLike[_ScalarT1], a1: _ArrayLike[_ScalarT2], /) -> tuple[NDArray[_ScalarT1], NDArray[_ScalarT2]]: ...
@overload
def atleast_2d(a0: _ArrayLike[_ScalarT], a1: _ArrayLike[_ScalarT], /, *arys: _ArrayLike[_ScalarT]) -> tuple[NDArray[_ScalarT], ...]: ...
@overload
def atleast_2d(a0: ArrayLike, /) -> NDArray[Any]: ...
@overload
def atleast_2d(a0: ArrayLike, a1: ArrayLike, /) -> tuple[NDArray[Any], NDArray[Any]]: ...
@overload
def atleast_2d(a0: ArrayLike, a1: ArrayLike, /, *ai: ArrayLike) -> tuple[NDArray[Any], ...]: ...

# keep in sync with `numpy.ma.extras.atleast_3d`
@overload
def atleast_3d(a0: _ArrayLike[_ScalarT], /) -> NDArray[_ScalarT]: ...
@overload
def atleast_3d(a0: _ArrayLike[_ScalarT1], a1: _ArrayLike[_ScalarT2], /) -> tuple[NDArray[_ScalarT1], NDArray[_ScalarT2]]: ...
@overload
def atleast_3d(a0: _ArrayLike[_ScalarT], a1: _ArrayLike[_ScalarT], /, *arys: _ArrayLike[_ScalarT]) -> tuple[NDArray[_ScalarT], ...]: ...
@overload
def atleast_3d(a0: ArrayLike, /) -> NDArray[Any]: ...
@overload
def atleast_3d(a0: ArrayLike, a1: ArrayLike, /) -> tuple[NDArray[Any], NDArray[Any]]: ...
@overload
def atleast_3d(a0: ArrayLike, a1: ArrayLike, /, *ai: ArrayLike) -> tuple[NDArray[Any], ...]: ...

# used by numpy.lib._shape_base_impl
def _arrays_for_stack_dispatcher(arrays: Sequence[_T]) -> tuple[_T, ...]: ...

# keep in sync with `numpy.ma.extras.vstack`
@overload
def vstack(
    tup: Sequence[_ArrayLike[_ScalarT]],
    *,
    dtype: None = None,
    casting: _CastingKind = "same_kind"
) -> NDArray[_ScalarT]: ...
@overload
def vstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: _DTypeLike[_ScalarT],
    casting: _CastingKind = "same_kind"
) -> NDArray[_ScalarT]: ...
@overload
def vstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind"
) -> NDArray[Any]: ...

# keep in sync with `numpy.ma.extras.hstack`
@overload
def hstack(
    tup: Sequence[_ArrayLike[_ScalarT]],
    *,
    dtype: None = None,
    casting: _CastingKind = "same_kind"
) -> NDArray[_ScalarT]: ...
@overload
def hstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: _DTypeLike[_ScalarT],
    casting: _CastingKind = "same_kind"
) -> NDArray[_ScalarT]: ...
@overload
def hstack(
    tup: Sequence[ArrayLike],
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind"
) -> NDArray[Any]: ...

# keep in sync with `numpy.ma.extras.stack`
@overload
def stack(
    arrays: Sequence[_ArrayLike[_ScalarT]],
    axis: SupportsIndex = 0,
    out: None = None,
    *,
    dtype: None = None,
    casting: _CastingKind = "same_kind"
) -> NDArray[_ScalarT]: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex = 0,
    out: None = None,
    *,
    dtype: _DTypeLike[_ScalarT],
    casting: _CastingKind = "same_kind"
) -> NDArray[_ScalarT]: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex = 0,
    out: None = None,
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind"
) -> NDArray[Any]: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex,
    out: _ArrayT,
    *,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind",
) -> _ArrayT: ...
@overload
def stack(
    arrays: Sequence[ArrayLike],
    axis: SupportsIndex = 0,
    *,
    out: _ArrayT,
    dtype: DTypeLike | None = None,
    casting: _CastingKind = "same_kind",
) -> _ArrayT: ...

@overload
def unstack(
    array: _ArrayLike[_ScalarT],
    /,
    *,
    axis: int = 0,
) -> tuple[NDArray[_ScalarT], ...]: ...
@overload
def unstack(
    array: ArrayLike,
    /,
    *,
    axis: int = 0,
) -> tuple[NDArray[Any], ...]: ...

@overload
def block(arrays: _ArrayLike[_ScalarT]) -> NDArray[_ScalarT]: ...
@overload
def block(arrays: ArrayLike) -> NDArray[Any]: ...
