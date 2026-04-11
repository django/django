from typing import TypeAlias, assert_type

import numpy as np
import numpy.typing as npt

_ArrayND: TypeAlias = npt.NDArray[np.int64]
_Array2D: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.int8]]
_Array3D: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.bool]]

_nd: _ArrayND
_2d: _Array2D
_3d: _Array3D

# reshape
assert_type(_nd.reshape(None), npt.NDArray[np.int64])
assert_type(_nd.reshape(4), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(_nd.reshape((4,)), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(_nd.reshape(2, 2), np.ndarray[tuple[int, int], np.dtype[np.int64]])
assert_type(_nd.reshape((2, 2)), np.ndarray[tuple[int, int], np.dtype[np.int64]])

assert_type(_nd.reshape((2, 2), order="C"),  np.ndarray[tuple[int, int], np.dtype[np.int64]])
assert_type(_nd.reshape(4, order="C"),  np.ndarray[tuple[int], np.dtype[np.int64]])

# resize does not return a value

# transpose
assert_type(_nd.transpose(), npt.NDArray[np.int64])
assert_type(_nd.transpose(1, 0), npt.NDArray[np.int64])
assert_type(_nd.transpose((1, 0)), npt.NDArray[np.int64])

# swapaxes
assert_type(_nd.swapaxes(0, 1), _ArrayND)
assert_type(_2d.swapaxes(0, 1), _Array2D)
assert_type(_3d.swapaxes(0, 1), _Array3D)

# flatten
assert_type(_nd.flatten(), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(_nd.flatten("C"), np.ndarray[tuple[int], np.dtype[np.int64]])

# ravel
assert_type(_nd.ravel(), np.ndarray[tuple[int], np.dtype[np.int64]])
assert_type(_nd.ravel("C"), np.ndarray[tuple[int], np.dtype[np.int64]])

# squeeze
assert_type(_nd.squeeze(), npt.NDArray[np.int64])
assert_type(_nd.squeeze(0), npt.NDArray[np.int64])
assert_type(_nd.squeeze((0, 2)), npt.NDArray[np.int64])
