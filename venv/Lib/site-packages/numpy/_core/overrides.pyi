from collections.abc import Callable, Iterable
from typing import Any, Final, NamedTuple, ParamSpec, TypeAlias, TypeVar

from numpy._utils import set_module as set_module

_T = TypeVar("_T")
_Tss = ParamSpec("_Tss")
_FuncLikeT = TypeVar("_FuncLikeT", bound=type | Callable[..., object])

_Dispatcher: TypeAlias = Callable[_Tss, Iterable[object]]

###

ARRAY_FUNCTIONS: set[Callable[..., Any]] = ...
array_function_like_doc: Final[str] = ...

class ArgSpec(NamedTuple):
    args: list[str]
    varargs: str | None
    keywords: str | None
    defaults: tuple[Any, ...]

def get_array_function_like_doc(public_api: Callable[..., object], docstring_template: str = "") -> str: ...
def finalize_array_function_like(public_api: _FuncLikeT) -> _FuncLikeT: ...

#
def verify_matching_signatures(implementation: Callable[_Tss, object], dispatcher: _Dispatcher[_Tss]) -> None: ...

# NOTE: This actually returns a `_ArrayFunctionDispatcher` callable wrapper object, with
# the original wrapped callable stored in the `._implementation` attribute. It checks
# for any `__array_function__` of the values of specific arguments that the dispatcher
# specifies. Since the dispatcher only returns an iterable of passed array-like args,
# this overridable behaviour is impossible to annotate.
def array_function_dispatch(
    dispatcher: _Dispatcher[_Tss] | None = None,
    module: str | None = None,
    verify: bool = True,
    docs_from_dispatcher: bool = False,
) -> Callable[[_FuncLikeT], _FuncLikeT]: ...

#
def array_function_from_dispatcher(
    implementation: Callable[_Tss, _T],
    module: str | None = None,
    verify: bool = True,
    docs_from_dispatcher: bool = True,
) -> Callable[[_Dispatcher[_Tss]], Callable[_Tss, _T]]: ...
