from typing import Any, TypeAlias, TypeVar, assert_type, type_check_only

import numpy as np
import numpy.typing as npt

_ScalarT = TypeVar("_ScalarT", bound=np.generic)

_1D: TypeAlias = tuple[int]
_2D: TypeAlias = tuple[int, int]
_ND: TypeAlias = tuple[Any, ...]

_Indices2D: TypeAlias = tuple[
    np.ndarray[_1D, np.dtype[np.intp]],
    np.ndarray[_1D, np.dtype[np.intp]],
]

###

_nd_bool: np.ndarray[_ND, np.dtype[np.bool]]
_1d_bool: np.ndarray[_1D, np.dtype[np.bool]]
_2d_bool: np.ndarray[_2D, np.dtype[np.bool]]
_nd_u64: np.ndarray[_ND, np.dtype[np.uint64]]
_nd_i64: np.ndarray[_ND, np.dtype[np.int64]]
_nd_f64: np.ndarray[_ND, np.dtype[np.float64]]
_nd_c128: np.ndarray[_ND, np.dtype[np.complex128]]
_nd_obj: np.ndarray[_ND, np.dtype[np.object_]]

_to_nd_bool: list[bool] | list[list[bool]]
_to_1d_bool: list[bool]
_to_2d_bool: list[list[bool]]

_to_1d_f64: list[float]
_to_1d_c128: list[complex]

@type_check_only
def func1(ar: npt.NDArray[_ScalarT], a: int) -> npt.NDArray[_ScalarT]: ...
@type_check_only
def func2(ar: npt.NDArray[np.number], a: str) -> npt.NDArray[np.float64]: ...

@type_check_only
class _Cube:
    shape = 3, 4
    ndim = 2

###

# fliplr
assert_type(np.fliplr(_nd_bool), np.ndarray[_ND, np.dtype[np.bool]])
assert_type(np.fliplr(_1d_bool), np.ndarray[_1D, np.dtype[np.bool]])
assert_type(np.fliplr(_2d_bool), np.ndarray[_2D, np.dtype[np.bool]])
assert_type(np.fliplr(_to_nd_bool), np.ndarray)
assert_type(np.fliplr(_to_1d_bool), np.ndarray)
assert_type(np.fliplr(_to_2d_bool), np.ndarray)

# flipud
assert_type(np.flipud(_nd_bool), np.ndarray[_ND, np.dtype[np.bool]])
assert_type(np.flipud(_1d_bool), np.ndarray[_1D, np.dtype[np.bool]])
assert_type(np.flipud(_2d_bool), np.ndarray[_2D, np.dtype[np.bool]])
assert_type(np.flipud(_to_nd_bool), np.ndarray)
assert_type(np.flipud(_to_1d_bool), np.ndarray)
assert_type(np.flipud(_to_2d_bool), np.ndarray)

# eye
assert_type(np.eye(10), np.ndarray[_2D, np.dtype[np.float64]])
assert_type(np.eye(10, M=20, dtype=np.int64), np.ndarray[_2D, np.dtype[np.int64]])
assert_type(np.eye(10, k=2, dtype=int), np.ndarray[_2D])

# diag
assert_type(np.diag(_nd_bool), np.ndarray[_ND, np.dtype[np.bool]])
assert_type(np.diag(_1d_bool), np.ndarray[_2D, np.dtype[np.bool]])
assert_type(np.diag(_2d_bool), np.ndarray[_1D, np.dtype[np.bool]])
assert_type(np.diag(_to_nd_bool, k=0), np.ndarray)
assert_type(np.diag(_to_1d_bool, k=0), np.ndarray[_2D])
assert_type(np.diag(_to_2d_bool, k=0), np.ndarray[_1D])

# diagflat
assert_type(np.diagflat(_nd_bool), np.ndarray[_2D, np.dtype[np.bool]])
assert_type(np.diagflat(_1d_bool), np.ndarray[_2D, np.dtype[np.bool]])
assert_type(np.diagflat(_2d_bool), np.ndarray[_2D, np.dtype[np.bool]])
assert_type(np.diagflat(_to_nd_bool, k=0), np.ndarray[_2D])
assert_type(np.diagflat(_to_1d_bool, k=0), np.ndarray[_2D])
assert_type(np.diagflat(_to_2d_bool, k=0), np.ndarray[_2D])

# tri
assert_type(np.tri(10), np.ndarray[_2D, np.dtype[np.float64]])
assert_type(np.tri(10, M=20, dtype=np.int64), np.ndarray[_2D, np.dtype[np.int64]])
assert_type(np.tri(10, k=2, dtype=int), np.ndarray[_2D])

# tril
assert_type(np.tril(_nd_bool), np.ndarray[_ND, np.dtype[np.bool]])
assert_type(np.tril(_to_nd_bool, k=0), np.ndarray)
assert_type(np.tril(_to_1d_bool, k=0), np.ndarray)
assert_type(np.tril(_to_2d_bool, k=0), np.ndarray)

# triu
assert_type(np.triu(_nd_bool), np.ndarray[_ND, np.dtype[np.bool]])
assert_type(np.triu(_to_nd_bool, k=0), np.ndarray)
assert_type(np.triu(_to_1d_bool, k=0), np.ndarray)
assert_type(np.triu(_to_2d_bool, k=0), np.ndarray)

# vander
assert_type(np.vander(_nd_bool), np.ndarray[_2D, np.dtype[np.int_]])
assert_type(np.vander(_nd_u64), np.ndarray[_2D, np.dtype[np.uint64]])
assert_type(np.vander(_nd_i64, N=2), np.ndarray[_2D, np.dtype[np.int64]])
assert_type(np.vander(_nd_f64, increasing=True), np.ndarray[_2D, np.dtype[np.float64]])
assert_type(np.vander(_nd_c128), np.ndarray[_2D, np.dtype[np.complex128]])
assert_type(np.vander(_nd_obj), np.ndarray[_2D, np.dtype[np.object_]])

# histogram2d
assert_type(
    np.histogram2d(_to_1d_f64, _to_1d_f64),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
    ],
)
assert_type(
    np.histogram2d(_to_1d_c128, _to_1d_c128),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.complex128 | Any]],
        np.ndarray[_1D, np.dtype[np.complex128 | Any]],
    ],
)
assert_type(
    np.histogram2d(_nd_i64, _nd_bool),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
    ],
)
assert_type(
    np.histogram2d(_nd_f64, _nd_i64),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
    ],
)
assert_type(
    np.histogram2d(_nd_i64, _nd_f64),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.float64]],
    ],
)
assert_type(
    np.histogram2d(_nd_f64, _nd_c128, weights=_to_1d_bool),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.complex128]],
        np.ndarray[_1D, np.dtype[np.complex128]],
    ],
)
assert_type(
    np.histogram2d(_nd_f64, _nd_c128, bins=8),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.complex128]],
        np.ndarray[_1D, np.dtype[np.complex128]],
    ],
)
assert_type(
    np.histogram2d(_nd_c128, _nd_f64, bins=(8, 5)),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.complex128]],
        np.ndarray[_1D, np.dtype[np.complex128]],
    ],
)
assert_type(
    np.histogram2d(_nd_c128, _nd_i64, bins=_nd_u64),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.uint64]],
        np.ndarray[_1D, np.dtype[np.uint64]],
    ],
)
assert_type(
    np.histogram2d(_nd_c128, _nd_c128, bins=(_nd_u64, _nd_u64)),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.uint64]],
        np.ndarray[_1D, np.dtype[np.uint64]],
    ],
)
assert_type(
    np.histogram2d(_nd_c128, _nd_c128, bins=(_nd_bool, 8)),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.complex128 | np.bool]],
        np.ndarray[_1D, np.dtype[np.complex128 | np.bool]],
    ],
)
assert_type(
    np.histogram2d(_nd_c128, _nd_c128, bins=(_to_1d_f64, 8)),
    tuple[
        np.ndarray[_2D, np.dtype[np.float64]],
        np.ndarray[_1D, np.dtype[np.complex128 | Any]],
        np.ndarray[_1D, np.dtype[np.complex128 | Any]],
    ],
)

# mask_indices
assert_type(np.mask_indices(10, func1), _Indices2D)
assert_type(np.mask_indices(8, func2, "0"), _Indices2D)

# tril_indices
assert_type(np.tril_indices(3), _Indices2D)
assert_type(np.tril_indices(3, 1), _Indices2D)
assert_type(np.tril_indices(3, 1, 2), _Indices2D)
# tril_indices
assert_type(np.triu_indices(3), _Indices2D)
assert_type(np.triu_indices(3, 1), _Indices2D)
assert_type(np.triu_indices(3, 1, 2), _Indices2D)

# tril_indices_from
assert_type(np.tril_indices_from(_2d_bool), _Indices2D)
assert_type(np.tril_indices_from(_Cube()), _Indices2D)
# triu_indices_from
assert_type(np.triu_indices_from(_2d_bool), _Indices2D)
assert_type(np.triu_indices_from(_Cube()), _Indices2D)
