"""
This module provides the :module:`re2` backend for :class:`~pathspec.pathspec.PathSpec`.

WARNING: The *pathspec._backends.re2* package is not part of the public API. Its
contents and structure are likely to change.
"""
from __future__ import annotations

from collections.abc import (
	Sequence)
from typing import (
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional)  # Replaced by `X | None` in 3.10.

try:
	import re2
except ModuleNotFoundError:
	re2 = None

from pathspec.backend import (
	_Backend)
from pathspec.pattern import (
	RegexPattern)
from pathspec._typing import (
	override)  # Added in 3.12.

from .._utils import (
	enumerate_patterns)

from .base import (
	re2_error)
from ._base import (
	RE2_OPTIONS,
	Re2RegexDat,
	Re2RegexDebug)


class Re2PsBackend(_Backend):
	"""
	The :class:`Re2PsBackend` class is the :module:`re2` implementation used by
	:class:`~pathspec.pathspec.PathSpec` for matching files.
	"""

	def __init__(
		self,
		patterns: Sequence[RegexPattern],
		*,
		_debug_regex: Optional[bool] = None,
		_test_sort: Optional[Callable[[list], None]] = None,
	) -> None:
		"""
		Initialize the :class:`Re2PsBackend` instance.

		*patterns* (:class:`Sequence` of :class:`.RegexPattern`) contains the
		compiled patterns.
		"""
		if re2_error is not None:
			raise re2_error

		if patterns and not isinstance(patterns[0], RegexPattern):
			raise TypeError(f"{patterns[0]=!r} must be a RegexPattern.")

		use_patterns = dict(enumerate_patterns(
			patterns, filter=True, reverse=False,
		))
		regex_set = self._make_set()

		self._debug_regex = bool(_debug_regex)
		"""
		*_debug_regex* (:class:`bool`) is whether to include additional debugging
		information for the regular expressions.
		"""

		self._patterns: dict[int, RegexPattern] = use_patterns
		"""
		*_patterns* (:class:`dict`) maps pattern index (:class:`int`) to pattern
		(:class:`RegexPattern`).
		"""

		self._regex_data: list[Re2RegexDat] = self._init_set(
			debug=self._debug_regex,
			patterns=use_patterns,
			regex_set=regex_set,
			sort_indices=_test_sort,
		)
		"""
		*_regex_data* (:class:`list`) maps regex index (:class:`int`) to regex data
		(:class:`Re2RegexDat`).
		"""

		self._set: re2.Set = regex_set
		"""
		*_set* (:class:`re2.Set`) is the re2 regex set.
		"""

	@staticmethod
	def _init_set(
		debug: bool,
		patterns: dict[int, RegexPattern],
		regex_set: re2.Set,
		sort_indices: Optional[Callable[[list[int]], None]],
	) -> list[Re2RegexDat]:
		"""
		Create the re2 regex set.

		*debug* (:class:`bool`) is whether to include additional debugging
		information for the regular expressions.

		*patterns* (:class:`dict`) maps pattern index (:class:`int`) to pattern
		(:class:`.RegexPattern`).

		*regex_set* (:class:`re2.Set`) is the regex set.

		*sort_indices* (:class:`callable` or :data:`None`) is a function used to
		sort the patterns by index. This is used during testing to ensure the order
		of patterns is not accidentally relied on.

		Returns a :class:`list` indexed by regex id (:class:`int`) to its data
		(:class:`Re2RegexDat`).
		"""
		# Sort patterns.
		indices = list(patterns.keys())
		if sort_indices is not None:
			sort_indices(indices)

		# Prepare patterns.
		regex_data: list[Re2RegexDat] = []
		for pattern_index in indices:
			pattern = patterns[pattern_index]
			if pattern.include is None:
				continue

			assert isinstance(pattern, RegexPattern), pattern
			regex = pattern.regex.pattern

			if debug:
				regex_data.append(Re2RegexDebug(
					include=pattern.include,
					index=pattern_index,
					is_dir_pattern=False,
					regex=regex,
				))
			else:
				regex_data.append(Re2RegexDat(
					include=pattern.include,
					index=pattern_index,
					is_dir_pattern=False,
				))

			regex_set.Add(regex)

		# Compile patterns.
		regex_set.Compile()
		return regex_data

	@staticmethod
	def _make_set() -> re2.Set:
		"""
		Create the re2 regex set.

		Returns the set (:class:`re2.Set`).
		"""
		return re2.Set.SearchSet(RE2_OPTIONS)

	@override
	def match_file(self, file: str) -> tuple[Optional[bool], Optional[int]]:
		"""
		Check the file against the patterns.

		*file* (:class:`str`) is the normalized file path to check.

		Returns a :class:`tuple` containing whether to include *file* (:class:`bool`
		or :data:`None`), and the index of the last matched pattern (:class:`int` or
		:data:`None`).
		"""
		# Find best match.
		# - WARNING: According to the documentation on `RE2::Set::Match()`, there is
		#   no guarantee matches will be produced in order! Later expressions have
		#   higher priority.
		match_ids: Optional[list[int]] = self._set.Match(file)
		if not match_ids:
			return (None, None)

		regex_data = self._regex_data
		pattern_index = max(regex_data[__id].index for __id in match_ids)
		pattern = self._patterns[pattern_index]
		return (pattern.include, pattern_index)
