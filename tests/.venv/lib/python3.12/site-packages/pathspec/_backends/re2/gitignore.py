"""
This module provides the :module:`re2` backend for :class:`~pathspec.gitignore.GitIgnoreSpec`.

WARNING: The *pathspec._backends.re2* package is not part of the public API. Its
contents and structure are likely to change.
"""
from __future__ import annotations

from typing import (
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional,  # Replaced by `X | None` in 3.10.
	Union)  # Replaced by `X | Y` in 3.10.

try:
	import re2
except ModuleNotFoundError:
	re2 = None

from pathspec.pattern import (
	RegexPattern)
from pathspec.patterns.gitignore.spec import (
	GitIgnoreSpecPattern,
	_BYTES_ENCODING,
	_DIR_MARK_CG,
	_DIR_MARK_OPT)
from pathspec._typing import (
	override)  # Added in 3.12.

from ._base import (
	Re2RegexDat,
	Re2RegexDebug)
from .pathspec import (
	Re2PsBackend)


class Re2GiBackend(Re2PsBackend):
	"""
	The :class:`Re2GiBackend` class is the :module:`re2` implementation used by
	:class:`~pathspec.gitignore.GitIgnoreSpec` for matching files.
	"""

	@override
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

			use_regexes: list[tuple[Union[str, bytes], bool]] = []
			if isinstance(pattern, GitIgnoreSpecPattern):
				# GitIgnoreSpecPattern uses capture groups for its directory marker. Re2
				# supports capture groups, but they cannot be utilized when using
				# `re2.Set`. Handle this scenario.
				regex_str: str
				if isinstance(regex, str):
					regex_str = regex
				else:
					assert isinstance(regex, bytes), regex
					regex_str = regex.decode(_BYTES_ENCODING)

				if _DIR_MARK_CG in regex_str:
					# Found directory marker.
					if regex_str.endswith(_DIR_MARK_OPT):
						# Regex has optional directory marker. Split regex into directory
						# and file variants.
						base_regex = regex_str[:-len(_DIR_MARK_OPT)]
						use_regexes.append((f'{base_regex}/', True))
						use_regexes.append((f'{base_regex}$', False))
					else:
						# Remove capture group.
						base_regex = regex_str.replace(_DIR_MARK_CG, '/')
						use_regexes.append((base_regex, True))

			if not use_regexes:
				# No special case for regex.
				use_regexes.append((regex, False))

			for regex, is_dir_pattern in use_regexes:
				if debug:
					regex_data.append(Re2RegexDebug(
						include=pattern.include,
						index=pattern_index,
						is_dir_pattern=is_dir_pattern,
						regex=regex,
					))
				else:
					regex_data.append(Re2RegexDat(
						include=pattern.include,
						index=pattern_index,
						is_dir_pattern=is_dir_pattern,
					))

				regex_set.Add(regex)

		# Compile patterns.
		regex_set.Compile()
		return regex_data

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
		match_ids: Optional[list[int]] = self._set.Match(file)
		if not match_ids:
			return (None, None)

		out_include: Optional[bool] = None
		out_index: int = -1
		out_priority = -1

		regex_data = self._regex_data
		for regex_id in match_ids:
			regex_dat = regex_data[regex_id]

			is_dir_pattern = regex_dat.is_dir_pattern
			if is_dir_pattern:
				# Pattern matched by a directory pattern.
				priority = 1
			else:
				# Pattern matched by a file pattern.
				priority = 2

			# WARNING: According to the documentation on `RE2::Set::Match()`, there is
			# no guarantee matches will be produced in order!
			include = regex_dat.include
			index = regex_dat.index
			if (
				(include and is_dir_pattern and index > out_index)
				or (priority == out_priority and index > out_index)
				or priority > out_priority
			):
				out_include = include
				out_index = index
				out_priority = priority

		assert out_index != -1, (out_index, out_include, out_priority)
		return (out_include, out_index)
