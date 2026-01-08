"""
This module provides private data for the base implementation for the
:module:`re2` library.

WARNING: The *pathspec._backends.re2* package is not part of the public API. Its
contents and structure are likely to change.
"""
from __future__ import annotations

from dataclasses import (
	dataclass)
from typing import (
	Union)  # Replaced by `X | Y` in 3.10.

try:
	import re2
except ModuleNotFoundError:
	re2 = None
	RE2_OPTIONS = None
else:
	RE2_OPTIONS = re2.Options()
	RE2_OPTIONS.log_errors = False
	RE2_OPTIONS.never_capture = True

RE2_OPTIONS: re2.Options
"""
The re2 options to use:

-	`log_errors=False` disables logging to stderr.

-	`never_capture=True` disables capture groups because they effectively cannot
	be utilized with :class:`re2.Set`.
"""


@dataclass(frozen=True)
class Re2RegexDat(object):
	"""
	The :class:`Re2RegexDat` class is used to store data related to a regular
	expression.
	"""

	# The slots argument is not supported until Python 3.10.
	__slots__ = [
		'include',
		'index',
		'is_dir_pattern',
	]

	include: bool
	"""
	*include* (:class:`bool`) is whether is whether the matched files should be
	included (:data:`True`), or excluded (:data:`False`).
	"""

	index: int
	"""
	*index* (:class:`int`) is the pattern index.
	"""

	is_dir_pattern: bool
	"""
	*is_dir_pattern* (:class:`bool`) is whether the pattern is a directory
	pattern for gitignore.
	"""


@dataclass(frozen=True)
class Re2RegexDebug(Re2RegexDat):
	"""
	The :class:`Re2RegexDebug` class stores additional debug information related
	to a regular expression.
	"""

	# The slots argument is not supported until Python 3.10.
	__slots__ = ['regex']

	regex: Union[str, bytes]
	"""
	*regex* (:class:`str` or :class:`bytes`) is the regular expression.
	"""
