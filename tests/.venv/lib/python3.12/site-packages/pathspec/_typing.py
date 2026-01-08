"""
This module provides stubs for type hints not supported by all relevant Python
versions.

NOTICE: This project should have zero required dependencies which means it
cannot simply require :module:`typing_extensions`, and I do not want to maintain
a vendored copy of :module:`typing_extensions`.
"""

import functools
import warnings
from typing import (
	Any,
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional,  # Replaced by `X | None` in 3.10.
	TypeVar)
try:
	from typing import AnyStr  # Removed in 3.18.
except ImportError:
	AnyStr = TypeVar('AnyStr', str, bytes)
try:
	from typing import Never  # Added in 3.11.
except ImportError:
	from typing import NoReturn as Never

F = TypeVar('F', bound=Callable[..., Any])

try:
	from warnings import deprecated  # Added in 3.13.
except ImportError:
	try:
		from typing_extensions import deprecated
	except ImportError:
		def deprecated(
			message: str,
			/, *,
			category: Optional[type[Warning]] = DeprecationWarning,
			stacklevel: int = 1,
		) -> Callable[[F], F]:
			def decorator(f: F) -> F:
				@functools.wraps(f)
				def wrapper(*a, **k):
					warnings.warn(message, category=category, stacklevel=stacklevel+1)
					return f(*a, **k)
				return wrapper
			return decorator

try:
	from typing import override  # Added in 3.12.
except ImportError:
	try:
		from typing_extensions import override
	except ImportError:
		def override(f: F) -> F:
			return f


def assert_unreachable(message: str) -> Never:
	"""
	The code path is unreachable. Raises an :class:`AssertionError`.

	*message* (:class:`str`) is the error message.
	"""
	raise AssertionError(message)
