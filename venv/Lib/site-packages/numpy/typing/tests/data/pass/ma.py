import datetime as dt
from typing import Any, TypeAlias, TypeVar, cast

import numpy as np
import numpy.typing as npt
from numpy._typing import _Shape

_ScalarT = TypeVar("_ScalarT", bound=np.generic)
MaskedArray: TypeAlias = np.ma.MaskedArray[_Shape, np.dtype[_ScalarT]]

# mypy: disable-error-code=no-untyped-call

MAR_b: MaskedArray[np.bool] = np.ma.MaskedArray([True])
MAR_u: MaskedArray[np.uint32] = np.ma.MaskedArray([1], dtype=np.uint32)
MAR_i: MaskedArray[np.int64] = np.ma.MaskedArray([1])
MAR_f: MaskedArray[np.float64] = np.ma.MaskedArray([1.0])
MAR_c: MaskedArray[np.complex128] = np.ma.MaskedArray([1j])
MAR_td64: MaskedArray[np.timedelta64] = np.ma.MaskedArray([np.timedelta64(1, "D")])
MAR_dt64: MaskedArray[np.datetime64] = np.ma.MaskedArray([np.datetime64(1, "D")])
MAR_S: MaskedArray[np.bytes_] = np.ma.MaskedArray([b'foo'], dtype=np.bytes_)
MAR_U: MaskedArray[np.str_] = np.ma.MaskedArray(['foo'], dtype=np.str_)
MAR_T = cast(np.ma.MaskedArray[Any, np.dtypes.StringDType],
             np.ma.MaskedArray(["a"], dtype="T"))
MAR_V: MaskedArray[np.void] = np.ma.MaskedArray(
    [(1, 1)],
    mask=[(False, False)],
    dtype=[('a', int), ('b', int)]
)

AR_b: npt.NDArray[np.bool] = np.array([True, False, True])

AR_LIKE_b = [True]
AR_LIKE_u = [np.uint32(1)]
AR_LIKE_i = [1]
AR_LIKE_f = [1.0]
AR_LIKE_c = [1j]
AR_LIKE_m = [np.timedelta64(1, "D")]
AR_LIKE_M = [np.datetime64(1, "D")]

MAR_f.mask = AR_b
MAR_f.mask = np.False_

MAR_i.fill_value = 0

MAR_b.flat[MAR_i > 0] = False
MAR_i.flat[:] = 1
MAR_f.flat[[0]] = AR_LIKE_f
MAR_c.flat[[0, 0]] = [3, 4 + 3j]
MAR_td64.flat[0] = dt.timedelta(1)
MAR_dt64.flat[0] = dt.datetime(2020, 1, 1)

MAR_b[MAR_i > 0] = False
MAR_i[:] = 1
MAR_f[[0]] = AR_LIKE_f
MAR_c[[0, 0]] = [3, 4 + 3j]
MAR_td64[0] = dt.timedelta(1)
MAR_dt64[0] = dt.datetime(2020, 1, 1)
MAR_V['a'] = [2]

# Inplace addition

MAR_b += AR_LIKE_b

MAR_u += AR_LIKE_b
MAR_u += AR_LIKE_u

MAR_i += AR_LIKE_b
MAR_i += 2
MAR_i += AR_LIKE_i

MAR_f += AR_LIKE_b
MAR_f += 2
MAR_f += AR_LIKE_u
MAR_f += AR_LIKE_i
MAR_f += AR_LIKE_f

MAR_c += AR_LIKE_b
MAR_c += AR_LIKE_u
MAR_c += AR_LIKE_i
MAR_c += AR_LIKE_f
MAR_c += AR_LIKE_c

MAR_td64 += AR_LIKE_b
MAR_td64 += AR_LIKE_u
MAR_td64 += AR_LIKE_i
MAR_td64 += AR_LIKE_m
MAR_dt64 += AR_LIKE_b
MAR_dt64 += AR_LIKE_u
MAR_dt64 += AR_LIKE_i
MAR_dt64 += AR_LIKE_m

MAR_S += b'snakes'
MAR_U += 'snakes'
MAR_T += 'snakes'

# Inplace subtraction

MAR_u -= AR_LIKE_b
MAR_u -= AR_LIKE_u

MAR_i -= AR_LIKE_b
MAR_i -= AR_LIKE_i

MAR_f -= AR_LIKE_b
MAR_f -= AR_LIKE_u
MAR_f -= AR_LIKE_i
MAR_f -= AR_LIKE_f

MAR_c -= AR_LIKE_b
MAR_c -= AR_LIKE_u
MAR_c -= AR_LIKE_i
MAR_c -= AR_LIKE_f
MAR_c -= AR_LIKE_c

MAR_td64 -= AR_LIKE_b
MAR_td64 -= AR_LIKE_u
MAR_td64 -= AR_LIKE_i
MAR_td64 -= AR_LIKE_m
MAR_dt64 -= AR_LIKE_b
MAR_dt64 -= AR_LIKE_u
MAR_dt64 -= AR_LIKE_i
MAR_dt64 -= AR_LIKE_m

# Inplace floor division

MAR_f //= AR_LIKE_b
MAR_f //= 2
MAR_f //= AR_LIKE_u
MAR_f //= AR_LIKE_i
MAR_f //= AR_LIKE_f

MAR_td64 //= AR_LIKE_i

# Inplace true division

MAR_f /= AR_LIKE_b
MAR_f /= 2
MAR_f /= AR_LIKE_u
MAR_f /= AR_LIKE_i
MAR_f /= AR_LIKE_f

MAR_c /= AR_LIKE_b
MAR_c /= AR_LIKE_u
MAR_c /= AR_LIKE_i
MAR_c /= AR_LIKE_f
MAR_c /= AR_LIKE_c

MAR_td64 /= AR_LIKE_i

# Inplace multiplication

MAR_b *= AR_LIKE_b

MAR_u *= AR_LIKE_b
MAR_u *= AR_LIKE_u

MAR_i *= AR_LIKE_b
MAR_i *= 2
MAR_i *= AR_LIKE_i

MAR_f *= AR_LIKE_b
MAR_f *= 2
MAR_f *= AR_LIKE_u
MAR_f *= AR_LIKE_i
MAR_f *= AR_LIKE_f

MAR_c *= AR_LIKE_b
MAR_c *= AR_LIKE_u
MAR_c *= AR_LIKE_i
MAR_c *= AR_LIKE_f
MAR_c *= AR_LIKE_c

MAR_td64 *= AR_LIKE_b
MAR_td64 *= AR_LIKE_u
MAR_td64 *= AR_LIKE_i
MAR_td64 *= AR_LIKE_f

MAR_S *= 2
MAR_U *= 2
MAR_T *= 2

# Inplace power

MAR_u **= AR_LIKE_b
MAR_u **= AR_LIKE_u

MAR_i **= AR_LIKE_b
MAR_i **= AR_LIKE_i

MAR_f **= AR_LIKE_b
MAR_f **= AR_LIKE_u
MAR_f **= AR_LIKE_i
MAR_f **= AR_LIKE_f

MAR_c **= AR_LIKE_b
MAR_c **= AR_LIKE_u
MAR_c **= AR_LIKE_i
MAR_c **= AR_LIKE_f
MAR_c **= AR_LIKE_c
