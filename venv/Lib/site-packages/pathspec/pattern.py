"""
This module provides the base definition for patterns.
"""
from __future__ import annotations

import re
from collections.abc import (
	Iterable,
	Iterator)
from dataclasses import (
	dataclass)
from typing import (
	Any,
	Optional,  # Replaced by `X | None` in 3.10.
	TypeVar,
	Union)  # Replaced by `X | Y` in 3.10.

from ._typing import (
	AnyStr,  # Removed in 3.18.
	deprecated,  # Added in 3.13.
	override)  # Added in 3.12.

RegexPatternSelf = TypeVar("RegexPatternSelf", bound='RegexPattern')
"""
:class:`.RegexPattern` self type hint to support Python v<3.11 using PEP 673
recommendation.
"""

class Pattern(object):
	"""
	The :class:`Pattern` class is the abstract definition of a pattern.
	"""

	# Make the class dict-less.
	__slots__ = (
		'include',
	)

	def __init__(self, include: Optional[bool]) -> None:
		"""
		Initializes the :class:`Pattern` instance.

		*include* (:class:`bool` or :data:`None`) is whether the matched files
		should be included (:data:`True`), excluded (:data:`False`), or is a
		null-operation (:data:`None`).
		"""

		self.include = include
		"""
		*include* (:class:`bool` or :data:`None`) is whether the matched files
		should be included (:data:`True`), excluded (:data:`False`), or is a
		null-operation (:data:`None`).
		"""

	@deprecated((
		"Pattern.match() is deprecated. Use Pattern.match_file() with a loop for "
		"similar results."
	))
	def match(self, files: Iterable[str]) -> Iterator[str]:
		"""
		.. version-deprecated:: 0.10.0
			This method is no longer used. Use the :meth:`self.match_file <.Pattern.match_file>`
			method with a loop for similar results.

		Matches this pattern against the specified files.

		*files* (:class:`~collections.abc.Iterable` of :class:`str`) contains each
		file relative to the root directory.

		Returns an :class:`~collections.abc.Iterable` yielding each matched file
		path (:class:`str`).
		"""
		for file in files:
			if self.match_file(file) is not None:
				yield file

	def match_file(self, file: str) -> Optional[Any]:
		"""
		Matches this pattern against the specified file.

		*file* (:class:`str`) is the normalized file path to match against.

		Returns the match result if *file* matched; otherwise, :data:`None`.
		"""
		raise NotImplementedError((
			"{cls.__module__}.{cls.__qualname__} must override match_file()."
		).format(cls=self.__class__))


class RegexPattern(Pattern):
	"""
	The :class:`RegexPattern` class is an implementation of a pattern using
	regular expressions.
	"""

	# Keep the class dict-less.
	__slots__ = (
		'pattern',
		'regex',
	)

	def __init__(
		self,
		pattern: Union[AnyStr, re.Pattern, None],
		include: Optional[bool] = None,
	) -> None:
		"""
		Initializes the :class:`RegexPattern` instance.

		*pattern* (:class:`str`, :class:`bytes`, :class:`re.Pattern`, or
		:data:`None`) is the pattern to compile into a regular expression.

		*include* (:class:`bool` or :data:`None`) must be :data:`None` unless
		*pattern* is a precompiled regular expression (:class:`re.Pattern`) in which
		case it is whether matched files should be included (:data:`True`), excluded
		(:data:`False`), or is a null operation (:data:`None`).

			.. note:: Subclasses do not need to support the *include* parameter.
		"""

		if isinstance(pattern, (str, bytes)):
			assert include is None, (
				f"include:{include!r} must be null when pattern:{pattern!r} is a string."
			)
			regex, include = self.pattern_to_regex(pattern)
			# NOTE: Make sure to allow a null regular expression to be
			# returned for a null-operation.
			if include is not None:
				regex = re.compile(regex)

		elif pattern is not None and hasattr(pattern, 'match'):
			# Assume pattern is a precompiled regular expression.
			# - NOTE: Used specified *include*.
			regex = pattern

		elif pattern is None:
			# NOTE: Make sure to allow a null pattern to be passed for a
			# null-operation.
			assert include is None, (
				f"include:{include!r} must be null when pattern:{pattern!r} is null."
			)
			regex = None

		else:
			raise TypeError(f"pattern:{pattern!r} is not a string, re.Pattern, or None.")

		super(RegexPattern, self).__init__(include)

		self.pattern: Union[AnyStr, re.Pattern, None] = pattern
		"""
		*pattern* (:class:`str`, :class:`bytes`, :class:`re.Pattern`, or
		:data:`None`) is the uncompiled, input pattern. This is for reference.
		"""

		self.regex: Optional[re.Pattern] = regex
		"""
		*regex* (:class:`re.Pattern` or :data:`None`) is the compiled regular
		expression for the pattern.
		"""

	def __copy__(self: RegexPatternSelf) -> RegexPatternSelf:
		"""
		Performa a shallow copy of the pattern.

		Returns the copy (:class:`RegexPattern`).
		"""
		other = self.__class__(self.regex, self.include)
		other.pattern = self.pattern
		return other

	def __eq__(self, other: RegexPattern) -> bool:
		"""
		Tests the equality of this regex pattern with *other* (:class:`RegexPattern`)
		by comparing their :attr:`~Pattern.include` and :attr:`~RegexPattern.regex`
		attributes.
		"""
		if isinstance(other, RegexPattern):
			return self.include == other.include and self.regex == other.regex
		else:
			return NotImplemented

	@override
	def match_file(self, file: AnyStr) -> Optional[RegexMatchResult]:
		"""
		Matches this pattern against the specified file.

		*file* (:class:`str` or :class:`bytes`) is the file path relative to the
		root directory (e.g., "relative/path/to/file").

		Returns the match result (:class:`.RegexMatchResult`) if *file* matched;
		otherwise, :data:`None`.
		"""
		if self.include is not None:
			match = self.regex.search(file)
			if match is not None:
				return RegexMatchResult(match)

		return None

	@classmethod
	def pattern_to_regex(
		cls,
		pattern: AnyStr,
	) -> tuple[Optional[AnyStr], Optional[bool]]:
		"""
		Convert the pattern into an uncompiled regular expression.

		*pattern* (:class:`str` or :class:`bytes`) is the pattern to convert into a
		regular expression.

		Returns a :class:`tuple` containing:

			-	*pattern* (:class:`str`, :class:`bytes` or :data:`None`) is the
				uncompiled regular expression .

			-	*include* (:class:`bool` or :data:`None`) is whether matched files
				should be included (:data:`True`), excluded (:data:`False`), or is a
				null-operation (:data:`None`).

			.. note:: The default implementation simply returns *pattern* and
			   :data:`True`.
		"""
		return pattern, True


@dataclass()
class RegexMatchResult(object):
	"""
	The :class:`RegexMatchResult` data class is used to return information about
	the matched regular expression.
	"""

	# Keep the class dict-less.
	__slots__ = (
		'match',
	)

	match: re.Match
	"""
	*match* (:class:`re.Match`) is the regex match result.
	"""
