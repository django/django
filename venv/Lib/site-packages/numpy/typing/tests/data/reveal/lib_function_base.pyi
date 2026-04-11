from collections.abc import Callable
from fractions import Fraction
from typing import Any, LiteralString, assert_type, type_check_only

import numpy as np
import numpy.typing as npt

f8: np.float64
AR_LIKE_b: list[bool]
AR_LIKE_i8: list[int]
AR_LIKE_f8: list[float]
AR_LIKE_c16: list[complex]
AR_LIKE_O: list[Fraction]

AR_u1: npt.NDArray[np.uint8]
AR_i8: npt.NDArray[np.int64]
AR_f2: npt.NDArray[np.float16]
AR_f4: npt.NDArray[np.float32]
AR_f8: npt.NDArray[np.float64]
AR_f10: npt.NDArray[np.longdouble]
AR_c8: npt.NDArray[np.complex64]
AR_c16: npt.NDArray[np.complex128]
AR_c20: npt.NDArray[np.clongdouble]
AR_m: npt.NDArray[np.timedelta64]
AR_M: npt.NDArray[np.datetime64]
AR_O: npt.NDArray[np.object_]
AR_b: npt.NDArray[np.bool]
AR_U: npt.NDArray[np.str_]
CHAR_AR_U: np.char.chararray[tuple[Any, ...], np.dtype[np.str_]]

AR_f8_1d: np.ndarray[tuple[int], np.dtype[np.float64]]
AR_f8_2d: np.ndarray[tuple[int, int], np.dtype[np.float64]]
AR_f8_3d: np.ndarray[tuple[int, int, int], np.dtype[np.float64]]
AR_c16_1d: np.ndarray[tuple[int], np.dtype[np.complex128]]

AR_b_list: list[npt.NDArray[np.bool]]

@type_check_only
def func(a: np.ndarray, posarg: bool = ..., /, arg: int = ..., *, kwarg: str = ...) -> np.ndarray: ...
@type_check_only
def func_f8(a: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]: ...

###

# vectorize
vectorized_func: np.vectorize
assert_type(vectorized_func.pyfunc, Callable[..., Any])
assert_type(vectorized_func.cache, bool)
assert_type(vectorized_func.signature, LiteralString | None)
assert_type(vectorized_func.otypes, LiteralString | None)
assert_type(vectorized_func.excluded, set[int | str])
assert_type(vectorized_func.__doc__, str | None)
assert_type(vectorized_func([1]), Any)
assert_type(np.vectorize(int), np.vectorize)
assert_type(
    np.vectorize(int, otypes="i", doc="doc", excluded=(), cache=True, signature=None),
    np.vectorize,
)

# rot90
assert_type(np.rot90(AR_f8_1d), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.rot90(AR_f8, k=2), npt.NDArray[np.float64])
assert_type(np.rot90(AR_LIKE_f8, axes=(0, 1)), np.ndarray)

# flip
assert_type(np.flip(AR_f8_1d), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.flip(AR_f8, axis=(0, 1)), npt.NDArray[np.float64])
assert_type(np.flip(AR_LIKE_f8, axis=0), np.ndarray)

# iterable
assert_type(np.iterable(1), bool)
assert_type(np.iterable([1]), bool)

# average
assert_type(np.average(AR_f8_2d), np.float64)
assert_type(np.average(AR_f8_2d, axis=1), npt.NDArray[np.float64])
assert_type(np.average(AR_f8_2d, keepdims=True), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.average(AR_f8), np.float64)
assert_type(np.average(AR_f8, axis=1), npt.NDArray[np.float64])
assert_type(np.average(AR_f8, keepdims=True), npt.NDArray[np.float64])
assert_type(np.average(AR_f8, returned=True), tuple[np.float64, np.float64])
assert_type(np.average(AR_f8, axis=1, returned=True), tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]])
assert_type(np.average(AR_f8, keepdims=True, returned=True), tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]])
assert_type(np.average(AR_LIKE_f8), np.float64)
assert_type(np.average(AR_LIKE_f8, weights=AR_f8), np.float64)
assert_type(np.average(AR_LIKE_f8, axis=1), npt.NDArray[np.float64])
assert_type(np.average(AR_LIKE_f8, keepdims=True), npt.NDArray[np.float64])
assert_type(np.average(AR_LIKE_f8, returned=True), tuple[np.float64, np.float64])
assert_type(np.average(AR_LIKE_f8, axis=1, returned=True), tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]])
assert_type(np.average(AR_LIKE_f8, keepdims=True, returned=True), tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]])
assert_type(np.average(AR_O), Any)
assert_type(np.average(AR_O, axis=1), np.ndarray)
assert_type(np.average(AR_O, keepdims=True), np.ndarray)
assert_type(np.average(AR_O, returned=True), tuple[Any, Any])
assert_type(np.average(AR_O, axis=1, returned=True), tuple[np.ndarray, np.ndarray])
assert_type(np.average(AR_O, keepdims=True, returned=True), tuple[np.ndarray, np.ndarray])

# asarray_chkfinite
assert_type(np.asarray_chkfinite(AR_f8_1d), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.asarray_chkfinite(AR_f8), npt.NDArray[np.float64])
assert_type(np.asarray_chkfinite(AR_LIKE_f8), np.ndarray)
assert_type(np.asarray_chkfinite(AR_f8, dtype=np.float64), npt.NDArray[np.float64])
assert_type(np.asarray_chkfinite(AR_f8, dtype=float), np.ndarray)

# piecewise
assert_type(np.piecewise(AR_f8_1d, AR_b, [func]), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.piecewise(AR_f8, AR_b, [func]), npt.NDArray[np.float64])
assert_type(np.piecewise(AR_f8, AR_b, [func_f8]), npt.NDArray[np.float64])
assert_type(np.piecewise(AR_f8, AR_b_list, [func]), npt.NDArray[np.float64])
assert_type(np.piecewise(AR_f8, AR_b_list, [func_f8]), npt.NDArray[np.float64])
assert_type(np.piecewise(AR_f8, AR_b_list, [func], True, -1, kwarg=""), npt.NDArray[np.float64])
assert_type(np.piecewise(AR_f8, AR_b_list, [func], True, arg=-1, kwarg=""), npt.NDArray[np.float64])
assert_type(np.piecewise(AR_LIKE_f8, AR_b_list, [func]), np.ndarray)
assert_type(np.piecewise(AR_LIKE_f8, AR_b_list, [func_f8]), npt.NDArray[np.float64])

# extract
assert_type(np.extract(AR_i8, AR_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.extract(AR_i8, AR_LIKE_b), np.ndarray[tuple[int], np.dtype[np.bool]])
assert_type(np.extract(AR_i8, AR_LIKE_i8), np.ndarray[tuple[int], np.dtype[np.int_]])
assert_type(np.extract(AR_i8, AR_LIKE_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.extract(AR_i8, AR_LIKE_c16), np.ndarray[tuple[int], np.dtype[np.complex128]])

# select
assert_type(np.select([AR_b], [AR_f8_1d]), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.select([AR_b], [AR_f8]), npt.NDArray[np.float64])

# places
assert_type(np.place(AR_f8, mask=AR_i8, vals=5.0), None)

# copy
assert_type(np.copy(AR_LIKE_f8), np.ndarray)
assert_type(np.copy(AR_U), npt.NDArray[np.str_])
assert_type(np.copy(CHAR_AR_U, "K", subok=True), np.char.chararray[tuple[Any, ...], np.dtype[np.str_]])
assert_type(np.copy(CHAR_AR_U, subok=True), np.char.chararray[tuple[Any, ...], np.dtype[np.str_]])
# pyright correctly infers `NDArray[str_]` here
assert_type(np.copy(CHAR_AR_U), np.ndarray[Any, Any])  # pyright: ignore[reportAssertTypeFailure]

# gradient
assert_type(np.gradient(AR_f8_1d, 1), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(
    np.gradient(AR_f8_2d, [1, 2], [2, 3.5, 4]),
    tuple[
        np.ndarray[tuple[int, int], np.dtype[np.float64]],
        np.ndarray[tuple[int, int], np.dtype[np.float64]],
    ],
)
assert_type(
    np.gradient(AR_f8_3d),
    tuple[
        np.ndarray[tuple[int, int, int], np.dtype[np.float64]],
        np.ndarray[tuple[int, int, int], np.dtype[np.float64]],
        np.ndarray[tuple[int, int, int], np.dtype[np.float64]],
    ],
)
assert_type(np.gradient(AR_f8), np.ndarray[tuple[int], np.dtype[np.float64]] | Any)
assert_type(np.gradient(AR_LIKE_f8, edge_order=2), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.gradient(AR_LIKE_c16, axis=0), np.ndarray[tuple[int], np.dtype[np.complex128]])

# diff
assert_type(np.diff("git", n=0), str)
assert_type(np.diff(AR_f8), npt.NDArray[np.float64])
assert_type(np.diff(AR_f8_1d, axis=0), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.diff(AR_f8_2d, axis=0), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.diff(AR_LIKE_f8, prepend=1.5), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.diff(AR_c16), npt.NDArray[np.complex128])
assert_type(np.diff(AR_c16_1d), np.ndarray[tuple[int], np.dtype[np.complex128]])
assert_type(np.diff(AR_LIKE_c16), np.ndarray[tuple[int], np.dtype[np.complex128]])

# interp
assert_type(np.interp(1, [1], AR_f8), np.float64)
assert_type(np.interp(1, [1], [1]), np.float64)
assert_type(np.interp(1, [1], AR_c16), np.complex128)
assert_type(np.interp(1, [1], [1j]), np.complex128)
assert_type(np.interp([1], [1], AR_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.interp([1], [1], [1]),  np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.interp([1], [1], AR_c16), np.ndarray[tuple[int], np.dtype[np.complex128]])
assert_type(np.interp([1], [1], [1j]), np.ndarray[tuple[int], np.dtype[np.complex128]])

# angle
assert_type(np.angle(1), np.float64)
assert_type(np.angle(1, deg=True), np.float64)
assert_type(np.angle(1j), np.float64)
assert_type(np.angle(f8), np.float64)
assert_type(np.angle(AR_b), npt.NDArray[np.float64])
assert_type(np.angle(AR_u1), npt.NDArray[np.float64])
assert_type(np.angle(AR_i8), npt.NDArray[np.float64])
assert_type(np.angle(AR_f2), npt.NDArray[np.float16])
assert_type(np.angle(AR_f4), npt.NDArray[np.float32])
assert_type(np.angle(AR_c8), npt.NDArray[np.float32])
assert_type(np.angle(AR_f8), npt.NDArray[np.float64])
assert_type(np.angle(AR_c16), npt.NDArray[np.float64])
assert_type(np.angle(AR_f10), npt.NDArray[np.longdouble])
assert_type(np.angle(AR_c20), npt.NDArray[np.longdouble])
assert_type(np.angle(AR_f8_1d), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.angle(AR_c16_1d), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.angle(AR_LIKE_b), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.angle(AR_LIKE_i8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.angle(AR_LIKE_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.angle(AR_LIKE_c16), np.ndarray[tuple[int], np.dtype[np.float64]])

# unwrap
assert_type(np.unwrap(AR_f2), npt.NDArray[np.float16])
assert_type(np.unwrap(AR_f8), npt.NDArray[np.float64])
assert_type(np.unwrap(AR_f10), npt.NDArray[np.longdouble])
assert_type(np.unwrap(AR_O), npt.NDArray[np.object_])
assert_type(np.unwrap(AR_f8_1d), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.unwrap(AR_f8_2d), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.unwrap(AR_f8_3d), np.ndarray[tuple[int, int, int], np.dtype[np.float64]])
assert_type(np.unwrap(AR_LIKE_b), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.unwrap(AR_LIKE_i8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.unwrap(AR_LIKE_f8), np.ndarray[tuple[int], np.dtype[np.float64]])

# sort_complex
assert_type(np.sort_complex(AR_u1), npt.NDArray[np.complex64])
assert_type(np.sort_complex(AR_f8), npt.NDArray[np.complex128])
assert_type(np.sort_complex(AR_f10), npt.NDArray[np.clongdouble])
assert_type(np.sort_complex(AR_f8_1d), np.ndarray[tuple[int], np.dtype[np.complex128]])
assert_type(np.sort_complex(AR_c16_1d), np.ndarray[tuple[int], np.dtype[np.complex128]])

# trim_zeros
assert_type(np.trim_zeros(AR_f8), npt.NDArray[np.float64])
assert_type(np.trim_zeros(AR_LIKE_f8), list[float])

# cov
assert_type(np.cov(AR_f8_1d), np.ndarray[tuple[()], np.dtype[np.float64]])
assert_type(np.cov(AR_f8_2d), npt.NDArray[np.float64])
assert_type(np.cov(AR_f8), npt.NDArray[np.float64])
assert_type(np.cov(AR_f8, AR_f8), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.cov(AR_c16, AR_c16), np.ndarray[tuple[int, int], np.dtype[np.complex128]])
assert_type(np.cov(AR_LIKE_f8), np.ndarray[tuple[()], np.dtype[np.float64]])
assert_type(np.cov(AR_LIKE_f8, AR_LIKE_f8), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.cov(AR_LIKE_f8, dtype=np.float16), np.ndarray[tuple[()], np.dtype[np.float16]])
assert_type(np.cov(AR_LIKE_f8, AR_LIKE_f8, dtype=np.float32), np.ndarray[tuple[int, int], np.dtype[np.float32]])
assert_type(np.cov(AR_f8, AR_f8, dtype=float), np.ndarray[tuple[int, int]])
assert_type(np.cov(AR_LIKE_f8, dtype=float), np.ndarray[tuple[()]])
assert_type(np.cov(AR_LIKE_f8, AR_LIKE_f8, dtype=float), np.ndarray[tuple[int, int]])

# corrcoef
assert_type(np.corrcoef(AR_f8_1d), np.float64)
assert_type(np.corrcoef(AR_f8_2d), np.ndarray[tuple[int, int], np.dtype[np.float64]] | np.float64)
assert_type(np.corrcoef(AR_f8), np.ndarray[tuple[int, int], np.dtype[np.float64]] | np.float64)
assert_type(np.corrcoef(AR_f8, AR_f8), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.corrcoef(AR_c16, AR_c16), np.ndarray[tuple[int, int], np.dtype[np.complex128]])
assert_type(np.corrcoef(AR_LIKE_f8), np.float64)
assert_type(np.corrcoef(AR_LIKE_f8, AR_LIKE_f8), np.ndarray[tuple[int, int], np.dtype[np.float64]])
assert_type(np.corrcoef(AR_LIKE_f8, dtype=np.float16), np.float16)
assert_type(np.corrcoef(AR_LIKE_f8, AR_LIKE_f8, dtype=np.float32), np.ndarray[tuple[int, int], np.dtype[np.float32]])
assert_type(np.corrcoef(AR_f8, AR_f8, dtype=float), np.ndarray[tuple[int, int]])
assert_type(np.corrcoef(AR_LIKE_f8, dtype=float), Any)
assert_type(np.corrcoef(AR_LIKE_f8, AR_LIKE_f8, dtype=float), np.ndarray[tuple[int, int]])

# window functions
assert_type(np.blackman(5), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.bartlett(6), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.hanning(4.5), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.hamming(0), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.kaiser(4, 5.9), np.ndarray[tuple[int], np.dtype[np.float64]])

# i0 (bessel function)
assert_type(np.i0(AR_i8), npt.NDArray[np.float64])

# sinc (cardinal sine function)
assert_type(np.sinc(1.0), np.float64)
assert_type(np.sinc(1j), np.complex128 | Any)
assert_type(np.sinc(AR_f8), npt.NDArray[np.float64])
assert_type(np.sinc(AR_c16), npt.NDArray[np.complex128])
assert_type(np.sinc(AR_LIKE_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.sinc(AR_LIKE_c16), np.ndarray[tuple[int], np.dtype[np.complex128]])

# median
assert_type(np.median(AR_f8, keepdims=False), np.float64)
assert_type(np.median(AR_c16, overwrite_input=True), np.complex128)
assert_type(np.median(AR_m), np.timedelta64)
assert_type(np.median(AR_O), Any)
assert_type(np.median(AR_f8, keepdims=True), npt.NDArray[np.float64])
assert_type(np.median(AR_f8, axis=0), npt.NDArray[np.float64])
assert_type(np.median(AR_c16, keepdims=True), npt.NDArray[np.complex128])
assert_type(np.median(AR_c16, axis=0), npt.NDArray[np.complex128])
assert_type(np.median(AR_LIKE_f8, keepdims=True), npt.NDArray[np.float64])
assert_type(np.median(AR_LIKE_c16, keepdims=True), npt.NDArray[np.complex128])
assert_type(np.median(AR_LIKE_f8, out=AR_c16), npt.NDArray[np.complex128])

# percentile
assert_type(np.percentile(AR_f8, 50), np.float64)
assert_type(np.percentile(AR_f8, 50, axis=1), npt.NDArray[np.float64])
assert_type(np.percentile(AR_f8, 50, axis=(1, 0)), npt.NDArray[np.float64])
assert_type(np.percentile(AR_f8, 50, keepdims=True), npt.NDArray[np.float64])
assert_type(np.percentile(AR_f8, 50, axis=0, keepdims=True), npt.NDArray[np.float64])
assert_type(np.percentile(AR_c16, 50), np.complex128)
assert_type(np.percentile(AR_m, 50), np.timedelta64)
assert_type(np.percentile(AR_M, 50, overwrite_input=True), np.datetime64)
assert_type(np.percentile(AR_O, 50), Any)
assert_type(np.percentile(AR_f8, [50]), npt.NDArray[np.float64])
assert_type(np.percentile(AR_f8, [50], axis=1), npt.NDArray[np.float64])
assert_type(np.percentile(AR_f8, [50], keepdims=True), npt.NDArray[np.float64])
assert_type(np.percentile(AR_c16, [50]), npt.NDArray[np.complex128])
assert_type(np.percentile(AR_m, [50]), npt.NDArray[np.timedelta64])
assert_type(np.percentile(AR_M, [50], method="nearest"), npt.NDArray[np.datetime64])
assert_type(np.percentile(AR_O, [50]), npt.NDArray[np.object_])
assert_type(np.percentile(AR_f8, [50], keepdims=True), npt.NDArray[np.float64])
assert_type(np.percentile(AR_f8, [50], out=AR_c16), npt.NDArray[np.complex128])

# quantile
assert_type(np.quantile(AR_f8, 0.50), np.float64)
assert_type(np.quantile(AR_f8, 0.50, axis=1), npt.NDArray[np.float64])
assert_type(np.quantile(AR_f8, 0.50, axis=(1, 0)), npt.NDArray[np.float64])
assert_type(np.quantile(AR_f8, 0.50, keepdims=True), npt.NDArray[np.float64])
assert_type(np.quantile(AR_f8, 0.50, axis=0, keepdims=True), npt.NDArray[np.float64])
assert_type(np.quantile(AR_c16, 0.50), np.complex128)
assert_type(np.quantile(AR_m, 0.50), np.timedelta64)
assert_type(np.quantile(AR_M, 0.50, overwrite_input=True), np.datetime64)
assert_type(np.quantile(AR_O, 0.50), Any)
assert_type(np.quantile(AR_f8, [0.50]), npt.NDArray[np.float64])
assert_type(np.quantile(AR_f8, [0.50], axis=1), npt.NDArray[np.float64])
assert_type(np.quantile(AR_f8, [0.50], keepdims=True), npt.NDArray[np.float64])
assert_type(np.quantile(AR_c16, [0.50]), npt.NDArray[np.complex128])
assert_type(np.quantile(AR_m, [0.50]), npt.NDArray[np.timedelta64])
assert_type(np.quantile(AR_M, [0.50], method="nearest"), npt.NDArray[np.datetime64])
assert_type(np.quantile(AR_O, [0.50]), npt.NDArray[np.object_])
assert_type(np.quantile(AR_f8, [0.50], keepdims=True), npt.NDArray[np.float64])
assert_type(np.quantile(AR_f8, [0.50], out=AR_c16), npt.NDArray[np.complex128])

# trapezoid
assert_type(np.trapezoid(AR_LIKE_f8), np.float64)
assert_type(np.trapezoid(AR_LIKE_f8, AR_LIKE_f8), np.float64)
assert_type(np.trapezoid(AR_LIKE_c16), np.complex128)
assert_type(np.trapezoid(AR_LIKE_c16, AR_LIKE_f8), np.complex128)
assert_type(np.trapezoid(AR_LIKE_f8, AR_LIKE_c16), np.complex128)
assert_type(np.trapezoid(AR_LIKE_O), float)
assert_type(np.trapezoid(AR_LIKE_O, AR_LIKE_f8), float)
assert_type(np.trapezoid(AR_f8), np.float64 | npt.NDArray[np.float64])
assert_type(np.trapezoid(AR_f8, AR_f8), np.float64 | npt.NDArray[np.float64])
assert_type(np.trapezoid(AR_c16), np.complex128 | npt.NDArray[np.complex128])
assert_type(np.trapezoid(AR_c16, AR_c16), np.complex128 | npt.NDArray[np.complex128])
assert_type(np.trapezoid(AR_m), np.timedelta64 | npt.NDArray[np.timedelta64])
assert_type(np.trapezoid(AR_O), npt.NDArray[np.object_] | Any)
assert_type(np.trapezoid(AR_O, AR_LIKE_f8), npt.NDArray[np.object_] | Any)

# meshgrid
assert_type(np.meshgrid(), tuple[()])
assert_type(
    np.meshgrid(AR_f8),
    tuple[
        np.ndarray[tuple[int], np.dtype[np.float64]],
    ],
)
assert_type(
    np.meshgrid(AR_c16, indexing="ij"),
    tuple[
        np.ndarray[tuple[int], np.dtype[np.complex128]],
    ],
)
assert_type(
    np.meshgrid(AR_i8, AR_f8, copy=False),
    tuple[
        np.ndarray[tuple[int, int], np.dtype[np.int64]],
        np.ndarray[tuple[int, int], np.dtype[np.float64]],
    ],
)
assert_type(
    np.meshgrid(AR_LIKE_f8, AR_f8),
    tuple[
        np.ndarray[tuple[int, int]],
        np.ndarray[tuple[int, int], np.dtype[np.float64]],
    ],
)
assert_type(
    np.meshgrid(AR_f8, AR_LIKE_f8),
    tuple[
        np.ndarray[tuple[int, int], np.dtype[np.float64]],
        np.ndarray[tuple[int, int]],
    ],
)
assert_type(
    np.meshgrid(AR_LIKE_f8, AR_LIKE_f8),
    tuple[
        np.ndarray[tuple[int, int]],
        np.ndarray[tuple[int, int]],
    ],
)
assert_type(
    np.meshgrid(AR_f8, AR_i8, AR_c16),
    tuple[
        np.ndarray[tuple[int, int, int], np.dtype[np.float64]],
        np.ndarray[tuple[int, int, int], np.dtype[np.int64]],
        np.ndarray[tuple[int, int, int], np.dtype[np.complex128]],
    ],
)
assert_type(np.meshgrid(AR_f8, AR_f8, AR_f8, AR_f8), tuple[npt.NDArray[np.float64], ...])
assert_type(np.meshgrid(AR_f8, AR_f8, AR_f8, AR_LIKE_f8), tuple[np.ndarray, ...])
assert_type(np.meshgrid(*AR_LIKE_f8), tuple[np.ndarray, ...])

# delete
assert_type(np.delete(AR_f8, np.s_[:5]), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.delete(AR_LIKE_f8, [0, 4, 9], axis=0), np.ndarray)

# insert
assert_type(np.insert(AR_f8, np.s_[:5], 5), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.insert(AR_LIKE_f8, [0, 4, 9], [0.5, 9.2, 7], axis=0), np.ndarray)

# append
assert_type(np.append(f8, f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.append(AR_f8, AR_f8), np.ndarray[tuple[int], np.dtype[np.float64]])
assert_type(np.append(AR_LIKE_f8, AR_LIKE_c16, axis=0), np.ndarray)
assert_type(np.append(AR_f8, AR_LIKE_f8, axis=0), np.ndarray)

# digitize
assert_type(np.digitize(4.5, [1]), np.intp)
assert_type(np.digitize(AR_f8, [1, 2, 3]), npt.NDArray[np.intp])
