"""
This module provides the base implementation for the :module:`re2` backend.

WARNING: The *pathspec._backends.re2* package is not part of the public API. Its
contents and structure are likely to change.
"""
from __future__ import annotations

from typing import (
	Optional)  # Replaced by `X | None` in 3.10.

from ._base import (
	re2_error)

re2_error: Optional[Exception]
"""
*re2_error* (:class:`Exception` or :data:`None`) is the re2 import error.
"""
