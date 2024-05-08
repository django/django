from numpy.core import _dtype_ctypes

_globals = globals()

for item in _dtype_ctypes.__dir__():
    _globals[item] = getattr(_dtype_ctypes, item)
