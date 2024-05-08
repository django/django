import pytest

from numpy import array_api as xp


@pytest.mark.parametrize(
    "x, indices, axis, expected",
    [
        ([2, 3], [1, 1, 0], 0,  [3, 3, 2]),
        ([2, 3], [1, 1, 0], -1, [3, 3, 2]),
        ([[2, 3]], [1], -1, [[3]]),
        ([[2, 3]], [0, 0], 0, [[2, 3], [2, 3]]),
    ],
)
def test_take_function(x, indices, axis, expected):
    """
    Indices respect relative order of a descending stable-sort

    See https://github.com/numpy/numpy/issues/20778
    """
    x = xp.asarray(x)
    indices = xp.asarray(indices)
    out = xp.take(x, indices, axis=axis)
    assert xp.all(out == xp.asarray(expected))
