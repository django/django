from typing import type_check_only

import numpy as np
import numpy.typing as npt

_0d_bool: np.bool
_nd_bool: npt.NDArray[np.bool]
_nd_td64: npt.NDArray[np.timedelta64]
_to_2d_bool: list[list[bool]]

@type_check_only
def func1(ar: np.ndarray, a: int) -> npt.NDArray[np.str_]: ...
@type_check_only
def func2(ar: np.ndarray, a: float) -> float: ...

###

np.eye(10, M=20.0)  # type: ignore[call-overload]
np.eye(10, k=2.5, dtype=int)  # type: ignore[call-overload]

np.diag(_nd_bool, k=0.5)  # type: ignore[call-overload]
np.diagflat(_nd_bool, k=0.5)  # type: ignore[call-overload]

np.tri(10, M=20.0)  # type: ignore[call-overload]
np.tri(10, k=2.5, dtype=int)  # type: ignore[call-overload]

np.tril(_nd_bool, k=0.5)  # type: ignore[call-overload]
np.triu(_nd_bool, k=0.5)  # type: ignore[call-overload]

np.vander(_nd_td64)  # type: ignore[type-var]

np.histogram2d(_nd_td64)  # type: ignore[call-overload]

np.mask_indices(10, func1)  # type: ignore[arg-type]
np.mask_indices(10, func2, 10.5)  # type: ignore[arg-type]

np.tril_indices(3.14)  # type: ignore[arg-type]

np.tril_indices_from(_to_2d_bool)  # type: ignore[arg-type]
