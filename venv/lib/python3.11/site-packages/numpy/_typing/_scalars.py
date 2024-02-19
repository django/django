from typing import Union, Any

import numpy as np

# NOTE: `_StrLike_co` and `_BytesLike_co` are pointless, as `np.str_` and
# `np.bytes_` are already subclasses of their builtin counterpart

_CharLike_co = Union[str, bytes]

# The 6 `<X>Like_co` type-aliases below represent all scalars that can be
# coerced into `<X>` (with the casting rule `same_kind`)
_BoolLike_co = Union[bool, np.bool_]
_UIntLike_co = Union[_BoolLike_co, np.unsignedinteger[Any]]
_IntLike_co = Union[_BoolLike_co, int, np.integer[Any]]
_FloatLike_co = Union[_IntLike_co, float, np.floating[Any]]
_ComplexLike_co = Union[_FloatLike_co, complex, np.complexfloating[Any, Any]]
_TD64Like_co = Union[_IntLike_co, np.timedelta64]

_NumberLike_co = Union[int, float, complex, np.number[Any], np.bool_]
_ScalarLike_co = Union[
    int,
    float,
    complex,
    str,
    bytes,
    np.generic,
]

# `_VoidLike_co` is technically not a scalar, but it's close enough
_VoidLike_co = Union[tuple[Any, ...], np.void]
