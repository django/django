from numpy.core import _dtype

_globals = globals()

for item in _dtype.__dir__():
    _globals[item] = getattr(_dtype, item)
