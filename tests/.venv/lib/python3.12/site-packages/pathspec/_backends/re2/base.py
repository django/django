"""
This module provides the base implementation for the :module:`re2` backend.

WARNING: The *pathspec._backends.re2* package is not part of the public API. Its
contents and structure are likely to change.
"""
from __future__ import annotations

from typing import (
	Optional)

try:
	import re2
	re2_error = None
except ModuleNotFoundError as e:
	re2 = None
	re2_error = e

re2_error: Optional[ModuleNotFoundError]
"""
*re2_error* (:class:`ModuleNotFoundError` or :data:`None`) is the re2 import
error.
"""
