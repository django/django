from typing import Any

import numpy as np
import numpy.typing as npt

class _Index:
    def __index__(self) -> int: ...

class _MyArray:
    def __array__(self) -> np.ndarray[tuple[int], np.dtypes.Float64DType]: ...

_index: _Index
_my_array: _MyArray
_something: Any
_dtype: np.dtype[np.int8]

_a_nd: np.flatiter[npt.NDArray[np.float64]]

###

_a_nd.base = _something  # type: ignore[misc]
_a_nd.coords = _something  # type: ignore[misc]
_a_nd.index = _something  # type: ignore[misc]

_a_nd.copy("C")  # type: ignore[call-arg]
_a_nd.copy(order="C")  # type: ignore[call-arg]

# NOTE: Contrary to `ndarray.__getitem__` its counterpart in `flatiter`
# does not accept objects with the `__array__` or `__index__` protocols;
# boolean indexing is just plain broken (gh-17175)
_a_nd[np.True_]  # type: ignore[call-overload]
_a_nd[_index]  # type: ignore[call-overload]
_a_nd[_my_array]  # type: ignore[call-overload]

# `dtype` and `copy` are no-ops in `flatiter.__array__`
_a_nd.__array__(_dtype)  # type: ignore[arg-type]
_a_nd.__array__(dtype=_dtype)  # type: ignore[call-arg]
_a_nd.__array__(copy=True)  # type: ignore[arg-type]
