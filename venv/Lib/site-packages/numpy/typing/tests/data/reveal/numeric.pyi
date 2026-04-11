"""
Tests for :mod:`_core.numeric`.

Does not include tests which fall under ``array_constructors``.

"""

from typing import Any, assert_type

import numpy as np
import numpy.typing as npt

class SubClass(npt.NDArray[np.int64]): ...

i8: np.int64

AR_b: npt.NDArray[np.bool]
AR_u8: npt.NDArray[np.uint64]
AR_i8: npt.NDArray[np.int64]
AR_f8: npt.NDArray[np.float64]
AR_c16: npt.NDArray[np.complex128]
AR_m: npt.NDArray[np.timedelta64]
AR_O: npt.NDArray[np.object_]

_sub_nd_i8: SubClass

_to_1d_bool: list[bool]
_to_1d_int: list[int]
_to_1d_float: list[float]
_to_1d_complex: list[complex]

###

assert_type(np.count_nonzero(i8), np.intp)
assert_type(np.count_nonzero(AR_i8), np.intp)
assert_type(np.count_nonzero(_to_1d_int), np.intp)
assert_type(np.count_nonzero(AR_i8, keepdims=True), npt.NDArray[np.intp])
assert_type(np.count_nonzero(AR_i8, axis=0), Any)

assert_type(np.isfortran(i8), bool)
assert_type(np.isfortran(AR_i8), bool)

assert_type(np.argwhere(i8), np.ndarray[tuple[int, int], np.dtype[np.intp]])
assert_type(np.argwhere(AR_i8), np.ndarray[tuple[int, int], np.dtype[np.intp]])

assert_type(np.flatnonzero(i8), np.ndarray[tuple[int], np.dtype[np.intp]])
assert_type(np.flatnonzero(AR_i8), np.ndarray[tuple[int], np.dtype[np.intp]])

# correlate
assert_type(np.correlate(AR_i8, AR_i8), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(np.correlate(AR_b, AR_b), np.ndarray[tuple[int], np.dtype[np.bool]])
assert_type(np.correlate(AR_u8, AR_u8), np.ndarray[tuple[int], np.dtype[np.uint64]])
assert_type(np.correlate(AR_i8, AR_i8), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(np.correlate(AR_f8, AR_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.correlate(AR_f8, AR_i8), np.ndarray[tuple[int], np.dtype[np.float64 | Any]])
assert_type(np.correlate(AR_c16, AR_c16), np.ndarray[tuple[int], np.dtype[np.complex128]])
assert_type(np.correlate(AR_c16, AR_f8), np.ndarray[tuple[int], np.dtype[np.complex128 | Any]])
assert_type(np.correlate(AR_m, AR_m), np.ndarray[tuple[int], np.dtype[np.timedelta64]])
assert_type(np.correlate(AR_i8, AR_m), np.ndarray[tuple[int], np.dtype[np.timedelta64 | Any]])
assert_type(np.correlate(AR_O, AR_O), np.ndarray[tuple[int], np.dtype[np.object_]])
assert_type(np.correlate(_to_1d_bool, _to_1d_bool), np.ndarray[tuple[int], np.dtype[np.bool]])
assert_type(np.correlate(_to_1d_int, _to_1d_int), np.ndarray[tuple[int], np.dtype[np.int_ | Any]])
assert_type(np.correlate(_to_1d_float, _to_1d_float), np.ndarray[tuple[int], np.dtype[np.float64 | Any]])
assert_type(np.correlate(_to_1d_complex, _to_1d_complex), np.ndarray[tuple[int], np.dtype[np.complex128 | Any]])

# convolve (same as correlate)
assert_type(np.convolve(AR_i8, AR_i8), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(np.convolve(AR_b, AR_b), np.ndarray[tuple[int], np.dtype[np.bool]])
assert_type(np.convolve(AR_u8, AR_u8), np.ndarray[tuple[int], np.dtype[np.uint64]])
assert_type(np.convolve(AR_i8, AR_i8), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(np.convolve(AR_f8, AR_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.convolve(AR_f8, AR_i8), np.ndarray[tuple[int], np.dtype[np.float64 | Any]])
assert_type(np.convolve(AR_c16, AR_c16), np.ndarray[tuple[int], np.dtype[np.complex128]])
assert_type(np.convolve(AR_c16, AR_f8), np.ndarray[tuple[int], np.dtype[np.complex128 | Any]])
assert_type(np.convolve(AR_m, AR_m), np.ndarray[tuple[int], np.dtype[np.timedelta64]])
assert_type(np.convolve(AR_i8, AR_m), np.ndarray[tuple[int], np.dtype[np.timedelta64 | Any]])
assert_type(np.convolve(AR_O, AR_O), np.ndarray[tuple[int], np.dtype[np.object_]])
assert_type(np.convolve(_to_1d_bool, _to_1d_bool), np.ndarray[tuple[int], np.dtype[np.bool]])
assert_type(np.convolve(_to_1d_int, _to_1d_int), np.ndarray[tuple[int], np.dtype[np.int_ | Any]])
assert_type(np.convolve(_to_1d_float, _to_1d_float), np.ndarray[tuple[int], np.dtype[np.float64 | Any]])
assert_type(np.convolve(_to_1d_complex, _to_1d_complex), np.ndarray[tuple[int], np.dtype[np.complex128 | Any]])

# outer (very similar to above, but 2D output)
assert_type(np.outer(AR_i8, AR_i8), np.ndarray[tuple[int, int], np.dtype[np.int64]])
assert_type(np.outer(AR_b, AR_b), np.ndarray[tuple[int, int], np.dtype[np.bool]])
assert_type(np.outer(AR_u8, AR_u8), np.ndarray[tuple[int, int], np.dtype[np.uint64]])
assert_type(np.outer(AR_i8, AR_i8), np.ndarray[tuple[int, int], np.dtype[np.int64]])
assert_type(np.outer(AR_f8, AR_f8), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.outer(AR_f8, AR_i8), np.ndarray[tuple[int, int], np.dtype[np.float64 | Any]])
assert_type(np.outer(AR_c16, AR_c16), np.ndarray[tuple[int, int], np.dtype[np.complex128]])
assert_type(np.outer(AR_c16, AR_f8), np.ndarray[tuple[int, int], np.dtype[np.complex128 | Any]])
assert_type(np.outer(AR_m, AR_m), np.ndarray[tuple[int, int], np.dtype[np.timedelta64]])
assert_type(np.outer(AR_i8, AR_m), np.ndarray[tuple[int, int], np.dtype[np.timedelta64 | Any]])
assert_type(np.outer(AR_O, AR_O), np.ndarray[tuple[int, int], np.dtype[np.object_]])
assert_type(np.outer(AR_i8, AR_i8, out=_sub_nd_i8), SubClass)
assert_type(np.outer(_to_1d_bool, _to_1d_bool), np.ndarray[tuple[int, int], np.dtype[np.bool]])
assert_type(np.outer(_to_1d_int, _to_1d_int), np.ndarray[tuple[int, int], np.dtype[np.int_ | Any]])
assert_type(np.outer(_to_1d_float, _to_1d_float), np.ndarray[tuple[int, int], np.dtype[np.float64 | Any]])
assert_type(np.outer(_to_1d_complex, _to_1d_complex), np.ndarray[tuple[int, int], np.dtype[np.complex128 | Any]])

# tensordot
assert_type(np.tensordot(AR_i8, AR_i8), npt.NDArray[np.int64])
assert_type(np.tensordot(AR_b, AR_b), npt.NDArray[np.bool])
assert_type(np.tensordot(AR_u8, AR_u8), npt.NDArray[np.uint64])
assert_type(np.tensordot(AR_i8, AR_i8), npt.NDArray[np.int64])
assert_type(np.tensordot(AR_f8, AR_f8), npt.NDArray[np.float64])
assert_type(np.tensordot(AR_f8, AR_i8), npt.NDArray[np.float64 | Any])
assert_type(np.tensordot(AR_c16, AR_c16), npt.NDArray[np.complex128])
assert_type(np.tensordot(AR_c16, AR_f8), npt.NDArray[np.complex128 | Any])
assert_type(np.tensordot(AR_m, AR_m), npt.NDArray[np.timedelta64])
assert_type(np.tensordot(AR_O, AR_O), npt.NDArray[np.object_])
assert_type(np.tensordot(_to_1d_bool, _to_1d_bool), npt.NDArray[np.bool])
assert_type(np.tensordot(_to_1d_int, _to_1d_int), npt.NDArray[np.int_ | Any])
assert_type(np.tensordot(_to_1d_float, _to_1d_float), npt.NDArray[np.float64 | Any])
assert_type(np.tensordot(_to_1d_complex, _to_1d_complex), npt.NDArray[np.complex128 | Any])

# cross
assert_type(np.cross(AR_i8, AR_i8), npt.NDArray[np.int64])
assert_type(np.cross(AR_u8, AR_u8), npt.NDArray[np.uint64])
assert_type(np.cross(AR_i8, AR_i8), npt.NDArray[np.int64])
assert_type(np.cross(AR_f8, AR_f8), npt.NDArray[np.float64])
assert_type(np.cross(AR_f8, AR_i8), npt.NDArray[np.float64 | Any])
assert_type(np.cross(AR_c16, AR_c16), npt.NDArray[np.complex128])
assert_type(np.cross(AR_c16, AR_f8), npt.NDArray[np.complex128 | Any])
assert_type(np.cross(AR_m, AR_m), npt.NDArray[np.timedelta64])
assert_type(np.cross(AR_O, AR_O), npt.NDArray[np.object_])
assert_type(np.cross(_to_1d_int, _to_1d_int), npt.NDArray[np.int_ | Any])
assert_type(np.cross(_to_1d_float, _to_1d_float), npt.NDArray[np.float64 | Any])
assert_type(np.cross(_to_1d_complex, _to_1d_complex), npt.NDArray[np.complex128 | Any])

assert_type(np.isscalar(i8), bool)
assert_type(np.isscalar(AR_i8), bool)
assert_type(np.isscalar(_to_1d_int), bool)

assert_type(np.roll(AR_i8, 1), npt.NDArray[np.int64])
assert_type(np.roll(AR_i8, (1, 2)), npt.NDArray[np.int64])
assert_type(np.roll(_to_1d_int, 1), npt.NDArray[Any])

assert_type(np.rollaxis(AR_i8, 0, 1), npt.NDArray[np.int64])

assert_type(np.moveaxis(AR_i8, 0, 1), npt.NDArray[np.int64])
assert_type(np.moveaxis(AR_i8, (0, 1), (1, 2)), npt.NDArray[np.int64])

assert_type(np.indices([0, 1, 2]), npt.NDArray[np.int_])
assert_type(np.indices([0, 1, 2], sparse=True), tuple[npt.NDArray[np.int_], ...])
assert_type(np.indices([0, 1, 2], dtype=np.float64), npt.NDArray[np.float64])
assert_type(np.indices([0, 1, 2], sparse=True, dtype=np.float64), tuple[npt.NDArray[np.float64], ...])
assert_type(np.indices([0, 1, 2], dtype=float), npt.NDArray[Any])
assert_type(np.indices([0, 1, 2], sparse=True, dtype=float), tuple[npt.NDArray[Any], ...])

assert_type(np.binary_repr(1), str)

assert_type(np.base_repr(1), str)

assert_type(np.allclose(i8, AR_i8), bool)
assert_type(np.allclose(_to_1d_int, AR_i8), bool)
assert_type(np.allclose(AR_i8, AR_i8), bool)

assert_type(np.isclose(i8, i8), np.bool)
assert_type(np.isclose(i8, AR_i8), npt.NDArray[np.bool])
assert_type(np.isclose(_to_1d_int, _to_1d_int), np.ndarray[tuple[int], np.dtype[np.bool]])
assert_type(np.isclose(AR_i8, AR_i8), npt.NDArray[np.bool])

assert_type(np.array_equal(i8, AR_i8), bool)
assert_type(np.array_equal(_to_1d_int, AR_i8), bool)
assert_type(np.array_equal(AR_i8, AR_i8), bool)

assert_type(np.array_equiv(i8, AR_i8), bool)
assert_type(np.array_equiv(_to_1d_int, AR_i8), bool)
assert_type(np.array_equiv(AR_i8, AR_i8), bool)
