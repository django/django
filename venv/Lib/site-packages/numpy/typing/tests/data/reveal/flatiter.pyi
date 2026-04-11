from typing import Any, TypeAlias, assert_type

import numpy as np

_ArrayND: TypeAlias = np.ndarray[tuple[Any, ...], np.dtypes.StrDType]
_Array1D: TypeAlias = np.ndarray[tuple[int], np.dtypes.BytesDType]
_Array2D: TypeAlias = np.ndarray[tuple[int, int], np.dtypes.Int8DType]

_a_nd: np.flatiter[_ArrayND]
_a_1d: np.flatiter[_Array1D]
_a_2d: np.flatiter[_Array2D]

###

# .base
assert_type(_a_nd.base, _ArrayND)
assert_type(_a_1d.base, _Array1D)
assert_type(_a_2d.base, _Array2D)

# .coords
assert_type(_a_nd.coords, tuple[Any, ...])
assert_type(_a_1d.coords, tuple[int])
assert_type(_a_2d.coords, tuple[int, int])

# .index
assert_type(_a_nd.index, int)
assert_type(_a_1d.index, int)
assert_type(_a_2d.index, int)

# .__len__()
assert_type(len(_a_nd), int)
assert_type(len(_a_1d), int)
assert_type(len(_a_2d), int)

# .__iter__()
assert_type(iter(_a_nd), np.flatiter[_ArrayND])
assert_type(iter(_a_1d), np.flatiter[_Array1D])
assert_type(iter(_a_2d), np.flatiter[_Array2D])

# .__next__()
assert_type(next(_a_nd), np.str_)
assert_type(next(_a_1d), np.bytes_)
assert_type(next(_a_2d), np.int8)

# .__getitem__(())
assert_type(_a_nd[()], _ArrayND)
assert_type(_a_1d[()], _Array1D)
assert_type(_a_2d[()], _Array2D)
# .__getitem__(int)
assert_type(_a_nd[0], np.str_)
assert_type(_a_1d[0], np.bytes_)
assert_type(_a_2d[0], np.int8)
# .__getitem__(slice)
assert_type(_a_nd[::], np.ndarray[tuple[int], np.dtypes.StrDType])
assert_type(_a_1d[::], np.ndarray[tuple[int], np.dtypes.BytesDType])
assert_type(_a_2d[::], np.ndarray[tuple[int], np.dtypes.Int8DType])
# .__getitem__(EllipsisType)
assert_type(_a_nd[...], np.ndarray[tuple[int], np.dtypes.StrDType])
assert_type(_a_1d[...], np.ndarray[tuple[int], np.dtypes.BytesDType])
assert_type(_a_2d[...], np.ndarray[tuple[int], np.dtypes.Int8DType])
# .__getitem__(list[!])
assert_type(_a_nd[[]], np.ndarray[tuple[int], np.dtypes.StrDType])
assert_type(_a_1d[[]], np.ndarray[tuple[int], np.dtypes.BytesDType])
assert_type(_a_2d[[]], np.ndarray[tuple[int], np.dtypes.Int8DType])
# .__getitem__(list[int])
assert_type(_a_nd[[0]], np.ndarray[tuple[int], np.dtypes.StrDType])
assert_type(_a_1d[[0]], np.ndarray[tuple[int], np.dtypes.BytesDType])
assert_type(_a_2d[[0]], np.ndarray[tuple[int], np.dtypes.Int8DType])
# .__getitem__(list[list[int]])
assert_type(_a_nd[[[0]]], np.ndarray[tuple[int, int], np.dtypes.StrDType])
assert_type(_a_1d[[[0]]], np.ndarray[tuple[int, int], np.dtypes.BytesDType])
assert_type(_a_2d[[[0]]], np.ndarray[tuple[int, int], np.dtypes.Int8DType])
# .__getitem__(list[list[list[list[int]]]])
assert_type(_a_nd[[[[[0]]]]], np.ndarray[tuple[Any, ...], np.dtypes.StrDType])
assert_type(_a_1d[[[[[0]]]]], np.ndarray[tuple[Any, ...], np.dtypes.BytesDType])
assert_type(_a_2d[[[[[0]]]]], np.ndarray[tuple[Any, ...], np.dtypes.Int8DType])

# __array__()
assert_type(_a_nd.__array__(), np.ndarray[tuple[int], np.dtypes.StrDType])
assert_type(_a_1d.__array__(), np.ndarray[tuple[int], np.dtypes.BytesDType])
assert_type(_a_2d.__array__(), np.ndarray[tuple[int], np.dtypes.Int8DType])

# .copy()
assert_type(_a_nd.copy(), np.ndarray[tuple[int], np.dtypes.StrDType])
assert_type(_a_1d.copy(), np.ndarray[tuple[int], np.dtypes.BytesDType])
assert_type(_a_2d.copy(), np.ndarray[tuple[int], np.dtypes.Int8DType])
