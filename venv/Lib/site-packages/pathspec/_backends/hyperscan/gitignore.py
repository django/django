"""
This module provides the :module:`hyperscan` backend for :class:`~pathspec.gitignore.GitIgnoreSpec`.

WARNING: The *pathspec._backends.hyperscan* package is not part of the public
API. Its contents and structure are likely to change.
"""
from __future__ import annotations

from collections.abc import (
	Sequence)
from typing import (
	Any,
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional,  # Replaced by `X | None` in 3.10.
	Union)  # Replaced by `X | Y` in 3.10.

try:
	import hyperscan
except ModuleNotFoundError:
	hyperscan = None

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
	HS_FLAGS,
	HyperscanExprDat,
	HyperscanExprDebug)
from .pathspec import (
	HyperscanPsBackend)


class HyperscanGiBackend(HyperscanPsBackend):
	"""
	The :class:`HyperscanGiBackend` class is the :module:`hyperscan`
	implementation used by :class:`~pathspec.gitignore.GitIgnoreSpec`. The
	Hyperscan database uses block mode for matching files.
	"""

	# Change type hint.
	_out: tuple[Optional[bool], int, int]

	def __init__(
		self,
		patterns: Sequence[RegexPattern],
		*,
		_debug_exprs: Optional[bool] = None,
		_test_sort: Optional[Callable[[list], None]] = None,
	) -> None:
		"""
		Initialize the :class:`HyperscanMatcher` instance.

		*patterns* (:class:`Sequence` of :class:`.RegexPattern`) contains the
		compiled patterns.
		"""
		super().__init__(patterns, _debug_exprs=_debug_exprs, _test_sort=_test_sort)

		self._out = (None, -1, 0)
		"""
		*_out* (:class:`tuple`) stores the current match:

		-	*0* (:class:`bool` or :data:`None`) is the match include.

		-	*1* (:class:`int`) is the match index.

		-	*2* (:class:`int`) is the match priority.
		"""

	@override
	@staticmethod
	def _init_db(
		db: hyperscan.Database,
		debug: bool,
		patterns: list[tuple[int, RegexPattern]],
		sort_ids: Optional[Callable[[list[int]], None]],
	) -> list[HyperscanExprDat]:
		"""
		Create the Hyperscan database from the given patterns.

		*db* (:class:`hyperscan.Hyperscan`) is the Hyperscan database.

		*debug* (:class:`bool`) is whether to include additional debugging
		information for the expressions.

		*patterns* (:class:`~collections.abc.Sequence` of :class:`.RegexPattern`)
		contains the patterns.

		*sort_ids* (:class:`callable` or :data:`None`) is a function used to sort
		the compiled expression ids. This is used during testing to ensure the order
		of expressions is not accidentally relied on.

		Returns a :class:`list` indexed by expression id (:class:`int`) to its data
		(:class:`HyperscanExprDat`).
		"""
		# WARNING: Hyperscan raises a `hyperscan.error` exception when compiled with
		# zero elements.
		assert patterns, patterns

		# Prepare patterns.
		expr_data: list[HyperscanExprDat] = []
		exprs: list[bytes] = []
		for pattern_index, pattern in patterns:
			assert pattern.include is not None, (pattern_index, pattern)

			# Encode regex.
			assert isinstance(pattern, RegexPattern), pattern
			regex = pattern.regex.pattern

			use_regexes: list[tuple[Union[str, bytes], bool]] = []
			if isinstance(pattern, GitIgnoreSpecPattern):
				# GitIgnoreSpecPattern uses capture groups for its directory marker but
				# Hyperscan does not support capture groups. Handle this scenario.
				regex_str: str
				if isinstance(regex, str):
					regex_str: str = regex
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
				if isinstance(regex, bytes):
					regex_bytes = regex
				else:
					assert isinstance(regex, str), regex
					regex_bytes = regex.encode('utf8')

				if debug:
					expr_data.append(HyperscanExprDebug(
						include=pattern.include,
						index=pattern_index,
						is_dir_pattern=is_dir_pattern,
						regex=regex,
					))
				else:
					expr_data.append(HyperscanExprDat(
						include=pattern.include,
						index=pattern_index,
						is_dir_pattern=is_dir_pattern,
					))

				exprs.append(regex_bytes)

		# Sort expressions.
		ids = list(range(len(exprs)))
		if sort_ids is not None:
			sort_ids(ids)
			exprs = [exprs[__id] for __id in ids]

		# Compile patterns.
		db.compile(
			expressions=exprs,
			ids=ids,
			elements=len(exprs),
			flags=HS_FLAGS,
		)
		return expr_data

	@override
	def match_file(self, file: str) -> tuple[Optional[bool], Optional[int]]:
		"""
		Check the file against the patterns.

		*file* (:class:`str`) is the normalized file path to check.

		Returns a :class:`tuple` containing whether to include *file* (:class:`bool`
		or :data:`None`), and the index of the last matched pattern (:class:`int` or
		:data:`None`).
		"""
		# NOTICE: According to benchmarking, a method callback is 13% faster than
		# using a closure here.
		db = self._db
		if self._db is None:
			# Database was not initialized because there were no patterns. Return no
			# match.
			return (None, None)

		self._out = (None, -1, 0)
		db.scan(file.encode('utf8'), match_event_handler=self.__on_match)

		out_include, out_index = self._out[:2]
		if out_index == -1:
			out_index = None

		return (out_include, out_index)

	@override
	def __on_match(
		self,
		expr_id: int,
		_from: int,
		_to: int,
		_flags: int,
		_context: Any,
	) -> Optional[bool]:
		"""
		Called on each match.

		*expr_id* (:class:`int`) is the expression id (index) of the matched
		pattern.
		"""
		expr_dat = self._expr_data[expr_id]

		is_dir_pattern = expr_dat.is_dir_pattern
		if is_dir_pattern:
			# Pattern matched by a directory pattern.
			priority = 1
		else:
			# Pattern matched by a file pattern.
			priority = 2

		# WARNING: Hyperscan does not guarantee matches will be produced in order!
		include = expr_dat.include
		index = expr_dat.index
		prev_index = self._out[1]
		prev_priority = self._out[2]
		if (
			(include and is_dir_pattern and index > prev_index)
			or (priority == prev_priority and index > prev_index)
			or priority > prev_priority
		):
			self._out = (include, expr_dat.index, priority)
