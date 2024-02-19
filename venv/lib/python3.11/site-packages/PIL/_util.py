from __future__ import annotations

import os
from pathlib import Path
from typing import Any, NoReturn

from ._typing import TypeGuard


def is_path(f: Any) -> TypeGuard[bytes | str | Path]:
    return isinstance(f, (bytes, str, Path))


def is_directory(f: Any) -> TypeGuard[bytes | str | Path]:
    """Checks if an object is a string, and that it points to a directory."""
    return is_path(f) and os.path.isdir(f)


class DeferredError:
    def __init__(self, ex: BaseException):
        self.ex = ex

    def __getattr__(self, elt: str) -> NoReturn:
        raise self.ex

    @staticmethod
    def new(ex: BaseException) -> Any:
        """
        Creates an object that raises the wrapped exception ``ex`` when used,
        and casts it to :py:obj:`~typing.Any` type.
        """
        return DeferredError(ex)
