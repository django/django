"""
This module provides private utility functions for backends.

WARNING: The *pathspec._backends* package is not part of the public API. Its
contents and structure are likely to change.
"""

from collections.abc import (
	Iterable)
from typing import (
	TypeVar)

from pathspec.pattern import (
	Pattern)

TPattern = TypeVar("TPattern", bound=Pattern)


def enumerate_patterns(
	patterns: Iterable[TPattern],
	filter: bool,
	reverse: bool,
) -> list[tuple[int, TPattern]]:
	"""
	Enumerate the patterns.

	*patterns* (:class:`Iterable` of :class:`.Pattern`) contains the patterns.

	*filter* (:class:`bool`) is whether to remove no-op patterns (:data:`True`),
	or keep them (:data:`False`).

	*reverse* (:class:`bool`) is whether to reverse the pattern order
	(:data:`True`), or keep the order (:data:`True`).

	Returns the enumerated patterns (:class:`list` of :class:`tuple`).
	"""
	out_patterns = [
		(__i, __pat)
		for __i, __pat in enumerate(patterns)
		if not filter or __pat.include is not None
	]
	if reverse:
		out_patterns.reverse()

	return out_patterns
