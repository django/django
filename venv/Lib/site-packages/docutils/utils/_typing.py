# Copyright: This module has been placed in the public domain.
# Author: Adam Turner

"""Private helpers for the ``typing`` module."""

from __future__ import annotations

TYPE_CHECKING = False
if TYPE_CHECKING:
    import sys
    from collections.abc import Callable
    from typing import Any, Final, TypeVar, final, overload

    if sys.version_info[:2] >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self  # NoQA: F401

    if sys.version_info[:2] >= (3, 12):
        from typing import TypeAlias
    else:
        from typing_extensions import TypeAlias  # NoQA: F401

    _F = TypeVar("_F", bound=Callable[..., Any])
    _T = TypeVar('_T')
else:

    # Runtime replacement for ``typing.final``.
    def final(f: _T) -> _T:
        return f

    def _overload_inner(*args, **kwds):
        raise NotImplementedError

    # Runtime replacement for ``typing.overload``.
    def overload(func: _F) -> _F:
        return _overload_inner

__all__: Final = ('final', 'overload')
