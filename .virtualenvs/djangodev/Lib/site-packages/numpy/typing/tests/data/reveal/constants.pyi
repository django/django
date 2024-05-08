import sys
from typing import Literal

import numpy as np
from numpy.core._type_aliases import _SCTypes

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

assert_type(np.Inf, float)
assert_type(np.Infinity, float)
assert_type(np.NAN, float)
assert_type(np.NINF, float)
assert_type(np.NZERO, float)
assert_type(np.NaN, float)
assert_type(np.PINF, float)
assert_type(np.PZERO, float)
assert_type(np.e, float)
assert_type(np.euler_gamma, float)
assert_type(np.inf, float)
assert_type(np.infty, float)
assert_type(np.nan, float)
assert_type(np.pi, float)

assert_type(np.ALLOW_THREADS, int)
assert_type(np.BUFSIZE, Literal[8192])
assert_type(np.CLIP, Literal[0])
assert_type(np.ERR_CALL, Literal[3])
assert_type(np.ERR_DEFAULT, Literal[521])
assert_type(np.ERR_IGNORE, Literal[0])
assert_type(np.ERR_LOG, Literal[5])
assert_type(np.ERR_PRINT, Literal[4])
assert_type(np.ERR_RAISE, Literal[2])
assert_type(np.ERR_WARN, Literal[1])
assert_type(np.FLOATING_POINT_SUPPORT, Literal[1])
assert_type(np.FPE_DIVIDEBYZERO, Literal[1])
assert_type(np.FPE_INVALID, Literal[8])
assert_type(np.FPE_OVERFLOW, Literal[2])
assert_type(np.FPE_UNDERFLOW, Literal[4])
assert_type(np.MAXDIMS, Literal[32])
assert_type(np.MAY_SHARE_BOUNDS, Literal[0])
assert_type(np.MAY_SHARE_EXACT, Literal[-1])
assert_type(np.RAISE, Literal[2])
assert_type(np.SHIFT_DIVIDEBYZERO, Literal[0])
assert_type(np.SHIFT_INVALID, Literal[9])
assert_type(np.SHIFT_OVERFLOW, Literal[3])
assert_type(np.SHIFT_UNDERFLOW, Literal[6])
assert_type(np.UFUNC_BUFSIZE_DEFAULT, Literal[8192])
assert_type(np.WRAP, Literal[1])
assert_type(np.tracemalloc_domain, Literal[389047])

assert_type(np.little_endian, bool)
assert_type(np.True_, np.bool_)
assert_type(np.False_, np.bool_)

assert_type(np.UFUNC_PYVALS_NAME, Literal["UFUNC_PYVALS"])

assert_type(np.sctypeDict, dict[int | str, type[np.generic]])
assert_type(np.sctypes, _SCTypes)
