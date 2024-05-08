from numpy.core import multiarray

_globals = globals()

for item in multiarray.__dir__():
    _globals[item] = getattr(multiarray, item)
