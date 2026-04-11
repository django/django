from typing import Any, TypeVar, overload
from typing_extensions import deprecated

import numpy as np
from numpy import floating, object_
from numpy._typing import (
    NDArray,
    _ArrayLikeFloat_co,
    _ArrayLikeObject_co,
    _FloatLike_co,
)

__all__ = ["fix", "isneginf", "isposinf"]

_ArrayT = TypeVar("_ArrayT", bound=NDArray[Any])

@overload
@deprecated("np.fix will be deprecated in NumPy 2.5 in favor of np.trunc", category=PendingDeprecationWarning)
def fix(x: _FloatLike_co, out: None = None) -> floating: ...
@overload
@deprecated("np.fix will be deprecated in NumPy 2.5 in favor of np.trunc", category=PendingDeprecationWarning)
def fix(x: _ArrayLikeFloat_co, out: None = None) -> NDArray[floating]: ...
@overload
@deprecated("np.fix will be deprecated in NumPy 2.5 in favor of np.trunc", category=PendingDeprecationWarning)
def fix(x: _ArrayLikeObject_co, out: None = None) -> NDArray[object_]: ...
@overload
@deprecated("np.fix will be deprecated in NumPy 2.5 in favor of np.trunc", category=PendingDeprecationWarning)
def fix(x: _ArrayLikeFloat_co | _ArrayLikeObject_co, out: _ArrayT) -> _ArrayT: ...

@overload
def isposinf(  # type: ignore[misc]
    x: _FloatLike_co,
    out: None = None,
) -> np.bool: ...
@overload
def isposinf(
    x: _ArrayLikeFloat_co,
    out: None = None,
) -> NDArray[np.bool]: ...
@overload
def isposinf(
    x: _ArrayLikeFloat_co,
    out: _ArrayT,
) -> _ArrayT: ...

@overload
def isneginf(  # type: ignore[misc]
    x: _FloatLike_co,
    out: None = None,
) -> np.bool: ...
@overload
def isneginf(
    x: _ArrayLikeFloat_co,
    out: None = None,
) -> NDArray[np.bool]: ...
@overload
def isneginf(
    x: _ArrayLikeFloat_co,
    out: _ArrayT,
) -> _ArrayT: ...
