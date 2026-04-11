from _typeshed import Incomplete, SupportsLenAndGetItem
from collections.abc import Sequence
from typing import (
    Any,
    ClassVar,
    Final,
    Generic,
    Literal as L,
    Self,
    SupportsIndex,
    final,
    overload,
)
from typing_extensions import TypeVar

import numpy as np
from numpy import _CastingKind
from numpy._core.multiarray import ravel_multi_index, unravel_index
from numpy._typing import (
    ArrayLike,
    DTypeLike,
    NDArray,
    _AnyShape,
    _ArrayLike,
    _DTypeLike,
    _FiniteNestedSequence,
    _HasDType,
    _NestedSequence,
    _SupportsArray,
)

__all__ = [  # noqa: RUF022
    "ravel_multi_index",
    "unravel_index",
    "mgrid",
    "ogrid",
    "r_",
    "c_",
    "s_",
    "index_exp",
    "ix_",
    "ndenumerate",
    "ndindex",
    "fill_diagonal",
    "diag_indices",
    "diag_indices_from",
]

###

_T = TypeVar("_T")
_TupleT = TypeVar("_TupleT", bound=tuple[Any, ...])
_ArrayT = TypeVar("_ArrayT", bound=NDArray[Any])
_DTypeT = TypeVar("_DTypeT", bound=np.dtype)
_ScalarT = TypeVar("_ScalarT", bound=np.generic)
_ScalarT_co = TypeVar("_ScalarT_co", bound=np.generic, default=Any, covariant=True)
_BoolT_co = TypeVar("_BoolT_co", bound=bool, default=bool, covariant=True)

_AxisT_co = TypeVar("_AxisT_co", bound=int, default=L[0], covariant=True)
_MatrixT_co = TypeVar("_MatrixT_co", bound=bool, default=L[False], covariant=True)
_NDMinT_co = TypeVar("_NDMinT_co", bound=int, default=L[1], covariant=True)
_Trans1DT_co = TypeVar("_Trans1DT_co", bound=int, default=L[-1], covariant=True)

###

class ndenumerate(Generic[_ScalarT_co]):
    @overload
    def __init__(self: ndenumerate[_ScalarT], arr: _FiniteNestedSequence[_SupportsArray[np.dtype[_ScalarT]]]) -> None: ...
    @overload
    def __init__(self: ndenumerate[np.str_], arr: str | _NestedSequence[str]) -> None: ...
    @overload
    def __init__(self: ndenumerate[np.bytes_], arr: bytes | _NestedSequence[bytes]) -> None: ...
    @overload
    def __init__(self: ndenumerate[np.bool], arr: bool | _NestedSequence[bool]) -> None: ...
    @overload
    def __init__(self: ndenumerate[np.intp], arr: int | _NestedSequence[int]) -> None: ...
    @overload
    def __init__(self: ndenumerate[np.float64], arr: float | _NestedSequence[float]) -> None: ...
    @overload
    def __init__(self: ndenumerate[np.complex128], arr: complex | _NestedSequence[complex]) -> None: ...
    @overload
    def __init__(self: ndenumerate[Incomplete], arr: object) -> None: ...

    # The first overload is a (semi-)workaround for a mypy bug (tested with v1.10 and v1.11)
    @overload
    def __next__(
        self: ndenumerate[np.bool | np.number | np.flexible | np.datetime64 | np.timedelta64],
        /,
    ) -> tuple[_AnyShape, _ScalarT_co]: ...
    @overload
    def __next__(self: ndenumerate[np.object_], /) -> tuple[_AnyShape, Incomplete]: ...
    @overload
    def __next__(self, /) -> tuple[_AnyShape, _ScalarT_co]: ...

    #
    def __iter__(self) -> Self: ...

class ndindex:
    @overload
    def __init__(self, shape: tuple[SupportsIndex, ...], /) -> None: ...
    @overload
    def __init__(self, /, *shape: SupportsIndex) -> None: ...

    #
    def __iter__(self) -> Self: ...
    def __next__(self) -> _AnyShape: ...

class nd_grid(Generic[_BoolT_co]):
    __slots__ = ("sparse",)

    sparse: _BoolT_co
    def __init__(self, sparse: _BoolT_co = ...) -> None: ...  # stubdefaulter: ignore[missing-default]
    @overload
    def __getitem__(self: nd_grid[L[False]], key: slice | Sequence[slice]) -> NDArray[Incomplete]: ...
    @overload
    def __getitem__(self: nd_grid[L[True]], key: slice | Sequence[slice]) -> tuple[NDArray[Incomplete], ...]: ...

@final
class MGridClass(nd_grid[L[False]]):
    __slots__ = ()

    def __init__(self) -> None: ...

@final
class OGridClass(nd_grid[L[True]]):
    __slots__ = ()

    def __init__(self) -> None: ...

class AxisConcatenator(Generic[_AxisT_co, _MatrixT_co, _NDMinT_co, _Trans1DT_co]):
    __slots__ = "axis", "matrix", "ndmin", "trans1d"

    makemat: ClassVar[type[np.matrix[tuple[int, int], np.dtype]]]

    axis: _AxisT_co
    matrix: _MatrixT_co
    ndmin: _NDMinT_co
    trans1d: _Trans1DT_co

    # NOTE: mypy does not understand that these default values are the same as the
    # TypeVar defaults. Since the workaround would require us to write 16 overloads,
    # we ignore the assignment type errors here.
    def __init__(
        self,
        /,
        axis: _AxisT_co = 0,  # type: ignore[assignment]
        matrix: _MatrixT_co = False,  # type: ignore[assignment]
        ndmin: _NDMinT_co = 1,  # type: ignore[assignment]
        trans1d: _Trans1DT_co = -1,  # type: ignore[assignment]
    ) -> None: ...

    # TODO(jorenham): annotate this
    def __getitem__(self, key: Incomplete, /) -> Incomplete: ...
    def __len__(self, /) -> L[0]: ...

    # Keep in sync with _core.multiarray.concatenate
    @staticmethod
    @overload
    def concatenate(
        arrays: _ArrayLike[_ScalarT],
        /,
        axis: SupportsIndex | None = 0,
        out: None = None,
        *,
        dtype: None = None,
        casting: _CastingKind | None = "same_kind",
    ) -> NDArray[_ScalarT]: ...
    @staticmethod
    @overload
    def concatenate(
        arrays: SupportsLenAndGetItem[ArrayLike],
        /,
        axis: SupportsIndex | None = 0,
        out: None = None,
        *,
        dtype: _DTypeLike[_ScalarT],
        casting: _CastingKind | None = "same_kind",
    ) -> NDArray[_ScalarT]: ...
    @staticmethod
    @overload
    def concatenate(
        arrays: SupportsLenAndGetItem[ArrayLike],
        /,
        axis: SupportsIndex | None = 0,
        out: None = None,
        *,
        dtype: DTypeLike | None = None,
        casting: _CastingKind | None = "same_kind",
    ) -> NDArray[Incomplete]: ...
    @staticmethod
    @overload
    def concatenate(
        arrays: SupportsLenAndGetItem[ArrayLike],
        /,
        axis: SupportsIndex | None = 0,
        *,
        out: _ArrayT,
        dtype: DTypeLike | None = None,
        casting: _CastingKind | None = "same_kind",
    ) -> _ArrayT: ...
    @staticmethod
    @overload
    def concatenate(
        arrays: SupportsLenAndGetItem[ArrayLike],
        /,
        axis: SupportsIndex | None,
        out: _ArrayT,
        *,
        dtype: DTypeLike | None = None,
        casting: _CastingKind | None = "same_kind",
    ) -> _ArrayT: ...

@final
class RClass(AxisConcatenator[L[0], L[False], L[1], L[-1]]):
    __slots__ = ()

    def __init__(self, /) -> None: ...

@final
class CClass(AxisConcatenator[L[-1], L[False], L[2], L[0]]):
    __slots__ = ()

    def __init__(self, /) -> None: ...

class IndexExpression(Generic[_BoolT_co]):
    __slots__ = ("maketuple",)

    maketuple: _BoolT_co
    def __init__(self, maketuple: _BoolT_co) -> None: ...
    @overload
    def __getitem__(self, item: _TupleT) -> _TupleT: ...
    @overload
    def __getitem__(self: IndexExpression[L[True]], item: _T) -> tuple[_T]: ...
    @overload
    def __getitem__(self: IndexExpression[L[False]], item: _T) -> _T: ...

@overload
def ix_(*args: _FiniteNestedSequence[_HasDType[_DTypeT]]) -> tuple[np.ndarray[_AnyShape, _DTypeT], ...]: ...
@overload
def ix_(*args: str | _NestedSequence[str]) -> tuple[NDArray[np.str_], ...]: ...
@overload
def ix_(*args: bytes | _NestedSequence[bytes]) -> tuple[NDArray[np.bytes_], ...]: ...
@overload
def ix_(*args: bool | _NestedSequence[bool]) -> tuple[NDArray[np.bool], ...]: ...
@overload
def ix_(*args: int | _NestedSequence[int]) -> tuple[NDArray[np.intp], ...]: ...
@overload
def ix_(*args: float | _NestedSequence[float]) -> tuple[NDArray[np.float64], ...]: ...
@overload
def ix_(*args: complex | _NestedSequence[complex]) -> tuple[NDArray[np.complex128], ...]: ...

#
def fill_diagonal(a: NDArray[Any], val: object, wrap: bool = False) -> None: ...

#
def diag_indices(n: int, ndim: int = 2) -> tuple[NDArray[np.intp], ...]: ...
def diag_indices_from(arr: ArrayLike) -> tuple[NDArray[np.intp], ...]: ...

#
mgrid: Final[MGridClass] = ...
ogrid: Final[OGridClass] = ...

r_: Final[RClass] = ...
c_: Final[CClass] = ...

index_exp: Final[IndexExpression[L[True]]] = ...
s_: Final[IndexExpression[L[False]]] = ...
