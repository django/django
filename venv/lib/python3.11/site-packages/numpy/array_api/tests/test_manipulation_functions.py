from numpy.testing import assert_raises
import numpy as np

from .. import all
from .._creation_functions import asarray
from .._dtypes import float64, int8
from .._manipulation_functions import (
        concat,
        reshape,
        stack
)


def test_concat_errors():
    assert_raises(TypeError, lambda: concat((1, 1), axis=None))
    assert_raises(TypeError, lambda: concat([asarray([1], dtype=int8),
                                             asarray([1], dtype=float64)]))


def test_stack_errors():
    assert_raises(TypeError, lambda: stack([asarray([1, 1], dtype=int8),
                                            asarray([2, 2], dtype=float64)]))


def test_reshape_copy():
    a = asarray(np.ones((2, 3)))
    b = reshape(a, (3, 2), copy=True)
    assert not np.shares_memory(a._array, b._array)
    
    a = asarray(np.ones((2, 3)))
    b = reshape(a, (3, 2), copy=False)
    assert np.shares_memory(a._array, b._array)

    a = asarray(np.ones((2, 3)).T)
    b = reshape(a, (3, 2), copy=True)
    assert_raises(AttributeError, lambda: reshape(a, (2, 3), copy=False))

