"""
This module provides the base implementation for the :module:`hyperscan`
backend.

WARNING: The *pathspec._backends.hyperscan* package is not part of the public
API. Its contents and structure are likely to change.
"""
from __future__ import annotations

from typing import (
	Optional)

try:
	import hyperscan
	hyperscan_error = None
except ModuleNotFoundError as e:
	hyperscan = None
	hyperscan_error = e

hyperscan_error: Optional[ModuleNotFoundError]
"""
*hyperscan_error* (:class:`ModuleNotFoundError` or :data:`None`) is the
hyperscan import error.
"""
