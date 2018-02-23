""" This module contains type definitions and information about type availability. """

from collections.abc import Sequence

try:
    import numpy
except ImportError:
    NUMPY_IS_AVAILABLE = False
else:
    NUMPY_IS_AVAILABLE = True


if NUMPY_IS_AVAILABLE:
    # make ndarray instances identifiable as Sequence
    # see also https://github.com/numpy/numpy/issues/2776
    Sequence.register(numpy.ndarray)


__all__ = ['NUMPY_IS_AVAILABLE', Sequence.__name__
           ]
