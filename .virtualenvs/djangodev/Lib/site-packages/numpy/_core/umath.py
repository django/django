from numpy.core import umath

_globals = globals()

for item in umath.__dir__():
    _globals[item] = getattr(umath, item)
