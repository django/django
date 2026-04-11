import numpy as np
from numpy._typing import NDArray
from numpy.testing import (
    TestCase,
    assert_,
    assert_allclose,
    assert_array_almost_equal_nulp,
    assert_raises,
)
from numpy.testing._private.utils import _ComparisonFunc

__all__ = [
    "TestCase",
    "almost",
    "approx",
    "assert_",
    "assert_allclose",
    "assert_almost_equal",
    "assert_array_almost_equal",
    "assert_array_almost_equal_nulp",
    "assert_array_approx_equal",
    "assert_array_compare",
    "assert_array_equal",
    "assert_array_less",
    "assert_close",
    "assert_equal",
    "assert_equal_records",
    "assert_mask_equal",
    "assert_not_equal",
    "assert_raises",
    "fail_if_array_equal",
]

def approx(
    a: object, b: object, fill_value: bool = True, rtol: float = 1e-5, atol: float = 1e-8
) -> np.ndarray[tuple[int], np.dtype[np.bool]]: ...
def almost(a: object, b: object, decimal: int = 6, fill_value: bool = True) -> np.ndarray[tuple[int], np.dtype[np.bool]]: ...

#
def assert_equal_records(a: NDArray[np.void], b: NDArray[np.void]) -> None: ...
def assert_equal(actual: object, desired: object, err_msg: str = "") -> None: ...
def fail_if_equal(actual: object, desired: object, err_msg: str = "") -> None: ...
def assert_almost_equal(
    actual: object, desired: object, decimal: int = 7, err_msg: str = "", verbose: bool = True
) -> None: ...

#
def assert_array_compare(
    comparison: _ComparisonFunc,
    x: object,
    y: object,
    err_msg: str = "",
    verbose: bool = True,
    header: str = "",
    fill_value: bool = True,
) -> None: ...
def assert_array_equal(x: object, y: object, err_msg: str = "", verbose: bool = True) -> None: ...
def fail_if_array_equal(x: object, y: object, err_msg: str = "", verbose: bool = True) -> None: ...
def assert_array_approx_equal(
    x: object, y: object, decimal: int = 6, err_msg: str = "", verbose: bool = True
) -> None: ...
def assert_array_almost_equal(
    x: object, y: object, decimal: int = 6, err_msg: str = "", verbose: bool = True
) -> None: ...
def assert_array_less(x: object, y: object, err_msg: str = "", verbose: bool = True) -> None: ...
def assert_mask_equal(m1: object, m2: object, err_msg: str = "") -> None: ...

assert_not_equal = fail_if_equal
assert_close = assert_almost_equal
