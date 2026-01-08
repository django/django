"""
This module provides the :module:`hyperscan` backend for :class:`~pathspec.pathspec.PathSpec`.

WARNING: The *pathspec._backends.hyperscan* package is not part of the public
API. Its contents and structure are likely to change.
"""
from __future__ import annotations

from collections.abc import (
	Sequence)
from typing import (
	Any,
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional)  # Replaced by `X | None` in 3.10.

try:
	import hyperscan
except ModuleNotFoundError:
	hyperscan = None

from pathspec.backend import (
	_Backend)
from pathspec.pattern import (
	RegexPattern)
from pathspec._typing import (
	override)  # Added in 3.12.

from .._utils import (
	enumerate_patterns)

from .base import (
	hyperscan_error)
from ._base import (
	HS_FLAGS,
	HyperscanExprDat,
	HyperscanExprDebug)


class HyperscanPsBackend(_Backend):
	"""
	The :class:`HyperscanPsBackend` class is the :module:`hyperscan`
	implementation used by :class:`~pathspec.pathspec.PathSpec` for matching
	files. The Hyperscan database uses block mode for matching files.
	"""

	def __init__(
		self,
		patterns: Sequence[RegexPattern],
		*,
		_debug_exprs: Optional[bool] = None,
		_test_sort: Optional[Callable[[list], None]] = None,
	) -> None:
		"""
		Initialize the :class:`HyperscanPsBackend` instance.

		*patterns* (:class:`Sequence` of :class:`.RegexPattern`) contains the
		compiled patterns.
		"""
		if hyperscan is None:
			raise hyperscan_error

		if patterns and not isinstance(patterns[0], RegexPattern):
			raise TypeError(f"{patterns[0]=!r} must be a RegexPattern.")

		use_patterns = enumerate_patterns(
			patterns, filter=True, reverse=False,
		)

		debug_exprs = bool(_debug_exprs)
		if use_patterns:
			db = self._make_db()
			expr_data = self._init_db(
				db=db,
				debug=debug_exprs,
				patterns=use_patterns,
				sort_ids=_test_sort,
			)
		else:
			# WARNING: The hyperscan database cannot be initialized with zero
			# patterns.
			db = None
			expr_data = []

		self._db: Optional[hyperscan.Database] = db
		"""
		*_db* (:class:`hyperscan.Database`) is the Hyperscan database.
		"""

		self._debug_exprs = debug_exprs
		"""
		*_debug_exprs* (:class:`bool`) is whether to include additional debugging
		information for the expressions.
		"""

		self._expr_data: list[HyperscanExprDat] = expr_data
		"""
		*_expr_data* (:class:`list`) maps expression index (:class:`int`) to
		expression data (:class:`:class:`HyperscanExprDat`).
		"""

		self._out: tuple[Optional[bool], int] = (None, -1)
		"""
		*_out* (:class:`tuple`) stores the current match:

		-	*0* (:class:`bool` or :data:`None`) is the match include.

		-	*1* (:class:`int`) is the match index.
		"""

		self._patterns: dict[int, RegexPattern] = dict(use_patterns)
		"""
		*_patterns* (:class:`dict`) maps pattern index (:class:`int`) to pattern
		(:class:`RegexPattern`).
		"""

	@staticmethod
	def _init_db(
		db: hyperscan.Database,
		debug: bool,
		patterns: list[tuple[int, RegexPattern]],
		sort_ids: Optional[Callable[[list[int]], None]],
	) -> list[HyperscanExprDat]:
		"""
		Initialize the Hyperscan database from the given patterns.

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

			if isinstance(regex, bytes):
				regex_bytes = regex
			else:
				assert isinstance(regex, str), regex
				regex_bytes = regex.encode('utf8')

			if debug:
				expr_data.append(HyperscanExprDebug(
					include=pattern.include,
					index=pattern_index,
					is_dir_pattern=False,
					regex=regex,
				))
			else:
				expr_data.append(HyperscanExprDat(
					include=pattern.include,
					index=pattern_index,
					is_dir_pattern=False,
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
		# NOTICE: According to benchmarking, a method callback is 20% faster than
		# using a closure here.
		db = self._db
		if self._db is None:
			# Database was not initialized because there were no patterns. Return no
			# match.
			return (None, None)

		self._out = (None, -1)
		db.scan(file.encode('utf8'), match_event_handler=self.__on_match)

		out_include, out_index = self._out
		if out_index == -1:
			out_index = None

		return (out_include, out_index)

	@staticmethod
	def _make_db() -> hyperscan.Database:
		"""
		Create the Hyperscan database.

		Returns the database (:class:`hyperscan.Database`).
		"""
		return hyperscan.Database(mode=hyperscan.HS_MODE_BLOCK)

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
		# Store match.
		# - WARNING: Hyperscan does not guarantee matches will be produced in order!
		#   Later expressions have higher priority.
		expr_dat = self._expr_data[expr_id]
		index = expr_dat.index
		prev_index = self._out[1]
		if index > prev_index:
			self._out = (expr_dat.include, index)
