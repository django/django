from numpy.core import _internal

_globals = globals()

for item in _internal.__dir__():
    _globals[item] = getattr(_internal, item)
