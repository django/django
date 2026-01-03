"""
This module provides :class:`.GitIgnoreSpec` which replicates
*.gitignore* behavior.
"""

from typing import (
	AnyStr,
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.
	Iterable,  # Replaced by `collections.abc.Iterable` in 3.9.
	Optional,  # Replaced by `X | None` in 3.10.
	Tuple,  # Replaced by `tuple` in 3.9.
	Type,  # Replaced by `type` in 3.9.
	TypeVar,
	Union,  # Replaced by `X | Y` in 3.10.
	cast,
	overload)

from .pathspec import (
	PathSpec)
from .pattern import (
	Pattern)
from .patterns.gitwildmatch import (
	GitWildMatchPattern,
	_DIR_MARK)
from .util import (
	_is_iterable)

Self = TypeVar("Self", bound="GitIgnoreSpec")
"""
:class:`GitIgnoreSpec` self type hint to support Python v<3.11 using PEP
673 recommendation.
"""


class GitIgnoreSpec(PathSpec):
	"""
	The :class:`GitIgnoreSpec` class extends :class:`pathspec.pathspec.PathSpec` to
	replicate *.gitignore* behavior.
	"""

	def __eq__(self, other: object) -> bool:
		"""
		Tests the equality of this gitignore-spec with *other* (:class:`GitIgnoreSpec`)
		by comparing their :attr:`~pathspec.pattern.Pattern`
		attributes. A non-:class:`GitIgnoreSpec` will not compare equal.
		"""
		if isinstance(other, GitIgnoreSpec):
			return super().__eq__(other)
		elif isinstance(other, PathSpec):
			return False
		else:
			return NotImplemented

	# Support reversed order of arguments from PathSpec.
	@overload
	@classmethod
	def from_lines(
		cls: Type[Self],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern]],
		lines: Iterable[AnyStr],
	) -> Self:
		...

	@overload
	@classmethod
	def from_lines(
		cls: Type[Self],
		lines: Iterable[AnyStr],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern], None] = None,
	) -> Self:
		...

	@classmethod
	def from_lines(
		cls: Type[Self],
		lines: Iterable[AnyStr],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern], None] = None,
	) -> Self:
		"""
		Compiles the pattern lines.

		*lines* (:class:`~collections.abc.Iterable`) yields each uncompiled
		pattern (:class:`str`). This simply has to yield each line so it can
		be a :class:`io.TextIOBase` (e.g., from :func:`open` or
		:class:`io.StringIO`) or the result from :meth:`str.splitlines`.

		*pattern_factory* can be :data:`None`, the name of a registered
		pattern factory (:class:`str`), or a :class:`~collections.abc.Callable`
		used to compile patterns. The callable must accept an uncompiled
		pattern (:class:`str`) and return the compiled pattern
		(:class:`pathspec.pattern.Pattern`).
		Default is :data:`None` for :class:`.GitWildMatchPattern`).

		Returns the :class:`GitIgnoreSpec` instance.
		"""
		if pattern_factory is None:
			pattern_factory = GitWildMatchPattern

		elif (isinstance(lines, (str, bytes)) or callable(lines)) and _is_iterable(pattern_factory):
			# Support reversed order of arguments from PathSpec.
			pattern_factory, lines = lines, pattern_factory

		self = super().from_lines(pattern_factory, lines)
		return cast(Self, self)

	@staticmethod
	def _match_file(
		patterns: Iterable[Tuple[int, GitWildMatchPattern]],
		file: str,
	) -> Tuple[Optional[bool], Optional[int]]:
		"""
		Check the file against the patterns.

		.. NOTE:: Subclasses of :class:`~pathspec.pathspec.PathSpec` may override
		   this method as an instance method. It does not have to be a static
		   method. The signature for this method is subject to change.

		*patterns* (:class:`~collections.abc.Iterable`) yields each indexed pattern
		(:class:`tuple`) which contains the pattern index (:class:`int`) and actual
		pattern (:class:`~pathspec.pattern.Pattern`).

		*file* (:class:`str`) is the normalized file path to be matched against
		*patterns*.

		Returns a :class:`tuple` containing whether to include *file* (:class:`bool`
		or :data:`None`), and the index of the last matched pattern (:class:`int` or
		:data:`None`).
		"""
		out_include: Optional[bool] = None
		out_index: Optional[int] = None
		out_priority = 0
		for index, pattern in patterns:
			if pattern.include is not None:
				match = pattern.match_file(file)
				if match is not None:
					# Pattern matched.

					# Check for directory marker.
					dir_mark = match.match.groupdict().get(_DIR_MARK)

					if dir_mark:
						# Pattern matched by a directory pattern.
						priority = 1
					else:
						# Pattern matched by a file pattern.
						priority = 2

					if pattern.include and dir_mark:
						out_include = pattern.include
						out_index = index
						out_priority = priority
					elif priority >= out_priority:
						out_include = pattern.include
						out_index = index
						out_priority = priority

		return out_include, out_index
