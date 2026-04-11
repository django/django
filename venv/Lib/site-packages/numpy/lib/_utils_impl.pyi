from _typeshed import SupportsWrite
from typing import LiteralString
from typing_extensions import TypeVar

import numpy as np

__all__ = ["get_include", "info", "show_runtime"]

_ScalarOrArrayT = TypeVar("_ScalarOrArrayT", bound=np.generic | np.ndarray)
_DTypeT = TypeVar("_DTypeT", bound=np.dtype)

###

def get_include() -> LiteralString: ...
def show_runtime() -> None: ...
def info(
    object: object = None, maxwidth: int = 76, output: SupportsWrite[str] | None = None, toplevel: str = "numpy"
) -> None: ...
def drop_metadata(dtype: _DTypeT, /) -> _DTypeT: ...

# used internally by `lib._function_base_impl._median`
def _median_nancheck(data: np.ndarray, result: _ScalarOrArrayT, axis: int) -> _ScalarOrArrayT: ...
