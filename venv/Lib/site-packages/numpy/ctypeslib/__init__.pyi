import ctypes
from ctypes import c_int64 as _c_intp

from ._ctypeslib import (
    __all__ as __all__,
    __doc__ as __doc__,
    _concrete_ndptr as _concrete_ndptr,
    _ndptr as _ndptr,
    as_array as as_array,
    as_ctypes as as_ctypes,
    as_ctypes_type as as_ctypes_type,
    c_intp as c_intp,
    load_library as load_library,
    ndpointer as ndpointer,
)
