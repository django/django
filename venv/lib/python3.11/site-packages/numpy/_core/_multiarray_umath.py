from numpy.core import _multiarray_umath

_globals = globals()

for item in _multiarray_umath.__dir__():
    _globals[item] = getattr(_multiarray_umath, item)
