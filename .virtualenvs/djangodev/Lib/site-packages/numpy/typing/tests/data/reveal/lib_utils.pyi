import sys
from io import StringIO
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt
from numpy.lib.utils import _Deprecate

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

AR: npt.NDArray[np.float64]
AR_DICT: dict[str, npt.NDArray[np.float64]]
FILE: StringIO

def func(a: int) -> bool: ...

class FuncProtocol(Protocol):
    def __call__(self, a: int) -> bool: ...

assert_type(np.deprecate(func), FuncProtocol)
assert_type(np.deprecate(), _Deprecate)

assert_type(np.deprecate_with_doc("test"), _Deprecate)
assert_type(np.deprecate_with_doc(None), _Deprecate)

assert_type(np.byte_bounds(AR), tuple[int, int])
assert_type(np.byte_bounds(np.float64()), tuple[int, int])

assert_type(np.who(None), None)
assert_type(np.who(AR_DICT), None)

assert_type(np.info(1, output=FILE), None)

assert_type(np.source(np.interp, output=FILE), None)

assert_type(np.lookfor("binary representation", output=FILE), None)

assert_type(np.safe_eval("1 + 1"), Any)
