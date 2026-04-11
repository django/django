from typing import Any, Callable, TypeVar


ModuleAware = TypeVar('ModuleAware', bound=Callable[..., Any])
