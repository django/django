import numpy as np
from numpy._core.numeric import normalize_axis_index, normalize_axis_tuple

__all__ = ["byte_bounds", "normalize_axis_tuple", "normalize_axis_index"]

# NOTE: In practice `byte_bounds` can (potentially) take any object
# implementing the `__array_interface__` protocol. The caveat is
# that certain keys, marked as optional in the spec, must be present for
#  `byte_bounds`. This concerns `"strides"` and `"data"`.
def byte_bounds(a: np.generic | np.ndarray) -> tuple[int, int]: ...
