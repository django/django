"""Typing tests for `core._ufunc_config`."""

import sys
from typing import Any, Protocol
from collections.abc import Callable

import numpy as np
from numpy.core._ufunc_config import _ErrDict

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

def func(a: str, b: int) -> None: ...

class FuncProtocol(Protocol):
    def __call__(self, a: str, b: int) -> None: ...

class Write:
    def write(self, value: str) -> None: ...

class SupportsWrite(Protocol):
    def write(self, s: str, /) -> object: ...

assert_type(np.seterr(all=None), _ErrDict)
assert_type(np.seterr(divide="ignore"), _ErrDict)
assert_type(np.seterr(over="warn"), _ErrDict)
assert_type(np.seterr(under="call"), _ErrDict)
assert_type(np.seterr(invalid="raise"), _ErrDict)
assert_type(np.geterr(), _ErrDict)

assert_type(np.setbufsize(4096), int)
assert_type(np.getbufsize(), int)

assert_type(np.seterrcall(func), Callable[[str, int], Any] | None | SupportsWrite)
assert_type(np.seterrcall(Write()), Callable[[str, int], Any] | None | SupportsWrite)
assert_type(np.geterrcall(), Callable[[str, int], Any] | None | SupportsWrite)

assert_type(np.errstate(call=func, all="call"), np.errstate[FuncProtocol])
assert_type(np.errstate(call=Write(), divide="log", over="log"), np.errstate[Write])
