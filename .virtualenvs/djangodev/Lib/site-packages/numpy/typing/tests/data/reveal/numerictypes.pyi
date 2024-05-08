import sys
from typing import Literal, Any

import numpy as np
from numpy.core.numerictypes import _CastFunc

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

assert_type(np.cast[int], _CastFunc)
assert_type(np.cast["i8"], _CastFunc)
assert_type(np.cast[np.int64], _CastFunc)

assert_type(np.maximum_sctype(np.float64), type[np.float64])
assert_type(np.maximum_sctype("f8"), type[Any])

assert_type(np.issctype(np.float64), bool)
assert_type(np.issctype("foo"), Literal[False])

assert_type(np.obj2sctype(np.float64), None | type[np.float64])
assert_type(np.obj2sctype(np.float64, default=False), bool | type[np.float64])
assert_type(np.obj2sctype("S8"), None | type[Any])
assert_type(np.obj2sctype("S8", default=None),  None | type[Any])
assert_type(np.obj2sctype("foo", default=False),  bool | type[Any])
assert_type(np.obj2sctype(1), None)
assert_type(np.obj2sctype(1, default=False), bool)

assert_type(np.issubclass_(np.float64, float), bool)
assert_type(np.issubclass_(np.float64, (int, float)), bool)
assert_type(np.issubclass_(1, 1), Literal[False])

assert_type(np.sctype2char("S8"), str)
assert_type(np.sctype2char(list), str)

assert_type(np.nbytes[int], int)
assert_type(np.nbytes["i8"], int)
assert_type(np.nbytes[np.int64], int)

assert_type(
    np.ScalarType,
    tuple[
        type[int],
        type[float],
        type[complex],
        type[bool],
        type[bytes],
        type[str],
        type[memoryview],
        type[np.bool_],
        type[np.csingle],
        type[np.cdouble],
        type[np.clongdouble],
        type[np.half],
        type[np.single],
        type[np.double],
        type[np.longdouble],
        type[np.byte],
        type[np.short],
        type[np.intc],
        type[np.int_],
        type[np.longlong],
        type[np.timedelta64],
        type[np.datetime64],
        type[np.object_],
        type[np.bytes_],
        type[np.str_],
        type[np.ubyte],
        type[np.ushort],
        type[np.uintc],
        type[np.uint],
        type[np.ulonglong],
        type[np.void],
    ],
)
assert_type(np.ScalarType[0], type[int])
assert_type(np.ScalarType[3], type[bool])
assert_type(np.ScalarType[8], type[np.csingle])
assert_type(np.ScalarType[10], type[np.clongdouble])

assert_type(np.typecodes["Character"], Literal["c"])
assert_type(np.typecodes["Complex"], Literal["FDG"])
assert_type(np.typecodes["All"], Literal["?bhilqpBHILQPefdgFDGSUVOMm"])
