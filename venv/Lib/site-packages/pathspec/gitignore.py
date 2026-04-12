"""
This module provides :class:`.GitIgnoreSpec` which replicates *.gitignore*
behavior, and handles edge-cases where Git's behavior differs from what's
documented. Git allows including files from excluded directories which directly
contradicts the documentation. This uses :class:`.GitIgnoreSpecPattern` to fully
replicate Git's handling.
"""
from __future__ import annotations

from collections.abc import (
	Iterable,
	Sequence)
from typing import (
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional,  # Replaced by `X | None` in 3.10.
	TypeVar,
	Union,  # Replaced by `X | Y` in 3.10.
	cast,
	overload)

from pathspec.backend import (
	BackendNamesHint,
	_Backend)
from pathspec._backends.agg import (
	make_gitignore_backend)
from pathspec.pathspec import (
	PathSpec)
from pathspec.pattern import (
	Pattern)
from pathspec.patterns.gitignore.basic import (
	GitIgnoreBasicPattern)
from pathspec.patterns.gitignore.spec import (
	GitIgnoreSpecPattern)
from pathspec._typing import (
	AnyStr,  # Removed in 3.18.
	override)  # Added in 3.12.
from pathspec.util import (
	_is_iterable,
	lookup_pattern)

Self = TypeVar("Self", bound='GitIgnoreSpec')
"""
:class:`.GitIgnoreSpec` self type hint to support Python v<3.11 using PEP 673
recommendation.
"""


class GitIgnoreSpec(PathSpec):
	"""
	The :class:`GitIgnoreSpec` class extends :class:`.PathSpec` to replicate
	*gitignore* behavior. This is uses :class:`.GitIgnoreSpecPattern` to fully
	replicate Git's handling.
	"""

	def __eq__(self, other: object) -> bool:
		"""
		Tests the equality of this gitignore-spec with *other* (:class:`.GitIgnoreSpec`)
		by comparing their :attr:`self.patterns <.PathSpec.patterns>` attributes. A
		non-:class:`GitIgnoreSpec` will not compare equal.
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
		cls: type[Self],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern], None],
		lines: Iterable[AnyStr],
		*,
		backend: Union[BackendNamesHint, str, None] = None,
		_test_backend_factory: Optional[Callable[[Sequence[Pattern]], _Backend]] = None,
	) -> Self:
		...

	@overload
	@classmethod
	def from_lines(
		cls: type[Self],
		lines: Iterable[AnyStr],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern], None] = None,
		*,
		backend: Union[BackendNamesHint, str, None] = None,
		_test_backend_factory: Optional[Callable[[Sequence[Pattern]], _Backend]] = None,
	) -> Self:
		...

	@override
	@classmethod
	def from_lines(
		cls: type[Self],
		lines: Iterable[AnyStr],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern], None] = None,
		*,
		backend: Union[BackendNamesHint, str, None] = None,
		_test_backend_factory: Optional[Callable[[Sequence[Pattern]], _Backend]] = None,
	) -> Self:
		"""
		Compiles the pattern lines.

		*lines* (:class:`~collections.abc.Iterable`) yields each uncompiled pattern
		(:class:`str`). This simply has to yield each line, so it can be a
		:class:`io.TextIOBase` (e.g., from :func:`open` or :class:`io.StringIO`) or
		the result from :meth:`str.splitlines`.

		*pattern_factory* does not need to be set for :class:`GitIgnoreSpec`. If
		set, it should be either ``"gitignore"`` or :class:`.GitIgnoreSpecPattern`.
		There is no guarantee it will work with any other pattern class. Default is
		:data:`None` for :class:`.GitIgnoreSpecPattern`.

		*backend* (:class:`str` or :data:`None`) is the pattern (regular expression)
		matching backend to use. Default is :data:`None` for "best" to use the best
		available backend. Priority of backends is: "re2", "hyperscan", "simple".
		The "simple" backend is always available.

		Returns the :class:`GitIgnoreSpec` instance.
		"""
		if (isinstance(lines, (str, bytes)) or callable(lines)) and _is_iterable(pattern_factory):
			# Support reversed order of arguments from PathSpec.
			pattern_factory, lines = lines, pattern_factory

		if pattern_factory is None:
			pattern_factory = GitIgnoreSpecPattern
		elif pattern_factory == 'gitignore':
			# Force use of GitIgnoreSpecPattern for "gitignore" to handle edge-cases.
			# This makes usage easier.
			pattern_factory = GitIgnoreSpecPattern

		if isinstance(pattern_factory, str):
			pattern_factory = lookup_pattern(pattern_factory)

		if issubclass(pattern_factory, GitIgnoreBasicPattern):
			raise TypeError((
				f"{pattern_factory=!r} cannot be {GitIgnoreBasicPattern} because it "
				f"will give unexpected results."
			))  # TypeError

		self = super().from_lines(pattern_factory, lines, backend=backend, _test_backend_factory=_test_backend_factory)
		return cast(Self, self)

	@override
	@staticmethod
	def _make_backend(
		name: BackendNamesHint,
		patterns: Sequence[Pattern],
	) -> _Backend:
		"""
		.. warning:: This method is not part of the public API. It is subject to
			change.

		Create the backend for the patterns.

		*name* (:class:`str`) is the name of the backend.

		*patterns* (:class:`~collections.abc.Sequence` of :class:`.Pattern`)
		contains the compiled patterns.

		Returns the backend (:class:`._Backend`).
		"""
		return make_gitignore_backend(name, patterns)
