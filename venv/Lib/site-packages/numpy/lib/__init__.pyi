from numpy._core.function_base import add_newdoc
from numpy._core.multiarray import add_docstring, tracemalloc_domain

# all submodules of `lib` are accessible at runtime through `__getattr__`,
# so we implicitly re-export them here
from . import (
    _array_utils_impl as _array_utils_impl,
    _arraypad_impl as _arraypad_impl,
    _arraysetops_impl as _arraysetops_impl,
    _arrayterator_impl as _arrayterator_impl,
    _datasource as _datasource,
    _format_impl as _format_impl,
    _function_base_impl as _function_base_impl,
    _histograms_impl as _histograms_impl,
    _index_tricks_impl as _index_tricks_impl,
    _iotools as _iotools,
    _nanfunctions_impl as _nanfunctions_impl,
    _npyio_impl as _npyio_impl,
    _polynomial_impl as _polynomial_impl,
    _scimath_impl as _scimath_impl,
    _shape_base_impl as _shape_base_impl,
    _stride_tricks_impl as _stride_tricks_impl,
    _twodim_base_impl as _twodim_base_impl,
    _type_check_impl as _type_check_impl,
    _ufunclike_impl as _ufunclike_impl,
    _utils_impl as _utils_impl,
    _version as _version,
    array_utils,
    format,
    introspect,
    mixins,
    npyio,
    scimath,
    stride_tricks,
)
from ._arrayterator_impl import Arrayterator
from ._version import NumpyVersion

__all__ = [
    "Arrayterator",
    "add_docstring",
    "add_newdoc",
    "array_utils",
    "format",
    "introspect",
    "mixins",
    "NumpyVersion",
    "npyio",
    "scimath",
    "stride_tricks",
    "tracemalloc_domain",
]
