from collections.abc import Iterable
from typing import Any, SupportsIndex, TypeVar, overload

from numpy import generic
from numpy._typing import ArrayLike, NDArray, _AnyShape, _ArrayLike, _ShapeLike

__all__ = ["broadcast_to", "broadcast_arrays", "broadcast_shapes"]

_ScalarT = TypeVar("_ScalarT", bound=generic)

class DummyArray:
    __array_interface__: dict[str, Any]
    base: NDArray[Any] | None
    def __init__(
        self,
        interface: dict[str, Any],
        base: NDArray[Any] | None = None,
    ) -> None: ...

@overload
def as_strided(
    x: _ArrayLike[_ScalarT],
    shape: Iterable[int] | None = None,
    strides: Iterable[int] | None = None,
    subok: bool = False,
    writeable: bool = True,
) -> NDArray[_ScalarT]: ...
@overload
def as_strided(
    x: ArrayLike,
    shape: Iterable[int] | None = None,
    strides: Iterable[int] | None = None,
    subok: bool = False,
    writeable: bool = True,
) -> NDArray[Any]: ...

@overload
def sliding_window_view(
    x: _ArrayLike[_ScalarT],
    window_shape: int | Iterable[int],
    axis: SupportsIndex | None = None,
    *,
    subok: bool = False,
    writeable: bool = False,
) -> NDArray[_ScalarT]: ...
@overload
def sliding_window_view(
    x: ArrayLike,
    window_shape: int | Iterable[int],
    axis: SupportsIndex | None = None,
    *,
    subok: bool = False,
    writeable: bool = False,
) -> NDArray[Any]: ...

@overload
def broadcast_to(
    array: _ArrayLike[_ScalarT],
    shape: int | Iterable[int],
    subok: bool = False,
) -> NDArray[_ScalarT]: ...
@overload
def broadcast_to(
    array: ArrayLike,
    shape: int | Iterable[int],
    subok: bool = False,
) -> NDArray[Any]: ...

def broadcast_shapes(*args: _ShapeLike) -> _AnyShape: ...
def broadcast_arrays(*args: ArrayLike, subok: bool = False) -> tuple[NDArray[Any], ...]: ...

# used internally by `lib._function_base_impl._parse_input_dimensions`
def _broadcast_shape(*args: ArrayLike) -> _AnyShape: ...
