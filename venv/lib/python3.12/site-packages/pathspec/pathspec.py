"""
This module provides :class:`.PathSpec` which is an object-oriented interface
for pattern matching of files.
"""
from __future__ import annotations

from collections.abc import (
	Collection,
	Iterable,
	Iterator,
	Sequence)
from itertools import (
	zip_longest)
from typing import (
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.2.
	Optional,  # Replaced by `X | None` in 3.10.
	TypeVar,
	Union,  # Replaced by `X | Y` in 3.10.
	cast)

Self = TypeVar("Self", bound='PathSpec')
"""
:class:`.PathSpec` self type hint to support Python v<3.11 using PEP 673
recommendation.
"""

from pathspec import util
from pathspec.backend import (
	_Backend,
	BackendNamesHint)
from pathspec._backends.agg import (
	make_pathspec_backend)
from pathspec.pattern import (
	Pattern)
from pathspec._typing import (
	AnyStr,  # Removed in 3.18.
	deprecated)  # Added in 3.13.
from pathspec.util import (
	CheckResult,
	StrPath,
	TStrPath,
	TreeEntry,
	_is_iterable,
	normalize_file)


class PathSpec(object):
	"""
	The :class:`PathSpec` class is a wrapper around a list of compiled
	:class:`.Pattern` instances.
	"""

	def __init__(
		self,
		patterns: Union[Sequence[Pattern], Iterable[Pattern]],
		*,
		backend: Union[BackendNamesHint, str, None] = None,
		_test_backend_factory: Optional[Callable[[Sequence[Pattern]], _Backend]] = None,
	) -> None:
		"""
		Initializes the :class:`.PathSpec` instance.

		*patterns* (:class:`~collections.abc.Sequence` or :class:`~collections.abc.Iterable`)
		contains each compiled pattern (:class:`.Pattern`). If not a sequence, it
		will be converted to a :class:`list`.

		*backend* (:class:`str` or :data:`None`) is the pattern (regular expression)
		matching backend to use. Default is :data:`None` for "best" to use the best
		available backend. Priority of backends is: "re2", "hyperscan", "simple".
		The "simple" backend is always available.
		"""
		if not isinstance(patterns, Sequence):
			patterns = list(patterns)

		if backend is None:
			backend = 'best'

		backend = cast(BackendNamesHint, backend)
		if _test_backend_factory is not None:
			use_backend = _test_backend_factory(patterns)
		else:
			use_backend = self._make_backend(backend, patterns)

		self._backend: _Backend = use_backend
		"""
		*_backend* (:class:`._Backend`) is the pattern (regular expression) matching
		backend.
		"""

		self._backend_name: BackendNamesHint = backend
		"""
		*_backend_name* (:class:`str`) is the name of backend to use.
		"""

		self.patterns: Sequence[Pattern] = patterns
		"""
		*patterns* (:class:`~collections.abc.Sequence` of :class:`.Pattern`)
		contains the compiled patterns.
		"""

	def __add__(self: Self, other: PathSpec) -> Self:
		"""
		Combines the :attr:`self.patterns <.PathSpec.patterns>` patterns from two
		:class:`PathSpec` instances.
		"""
		if isinstance(other, PathSpec):
			return self.__class__(self.patterns + other.patterns, backend=self._backend_name)
		else:
			return NotImplemented

	def __eq__(self, other: object) -> bool:
		"""
		Tests the equality of this path-spec with *other* (:class:`PathSpec`) by
		comparing their :attr:`self.patterns <.PathSpec.patterns>` attributes.
		"""
		if isinstance(other, PathSpec):
			paired_patterns = zip_longest(self.patterns, other.patterns)
			return all(a == b for a, b in paired_patterns)
		else:
			return NotImplemented

	def __iadd__(self: Self, other: PathSpec) -> Self:
		"""
		Adds the :attr:`self.patterns <.PathSpec.patterns>` from *other*
		(:class:`PathSpec`) to this instance.
		"""
		if isinstance(other, PathSpec):
			self.patterns += other.patterns
			self._backend = self._make_backend(self._backend_name, self.patterns)
			return self
		else:
			return NotImplemented

	def __len__(self) -> int:
		"""
		Returns the number of :attr:`self.patterns <.PathSpec.patterns>` this
		path-spec contains (:class:`int`).
		"""
		return len(self.patterns)

	def check_file(
		self,
		file: TStrPath,
		separators: Optional[Collection[str]] = None,
	) -> CheckResult[TStrPath]:
		"""
		Check the files against this path-spec.

		*file* (:class:`str` or :class:`os.PathLike`) is the file path to be matched
		against :attr:`self.patterns <.PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`.normalize_file` for more information.

		Returns the file check result (:class:`.CheckResult`).
		"""
		norm_file = normalize_file(file, separators)
		include, index = self._backend.match_file(norm_file)
		return CheckResult(file, include, index)

	def check_files(
		self,
		files: Iterable[TStrPath],
		separators: Optional[Collection[str]] = None,
	) -> Iterator[CheckResult[TStrPath]]:
		"""
		Check the files against this path-spec.

		*files* (:class:`~collections.abc.Iterable` of :class:`str` or
		:class:`os.PathLike`) contains the file paths to be checked against
		:attr:`self.patterns <.PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`.normalize_file` for more information.

		Returns an :class:`~collections.abc.Iterator` yielding each file check
		result (:class:`.CheckResult`).
		"""
		if not _is_iterable(files):
			raise TypeError(f"files:{files!r} is not an iterable.")

		for orig_file in files:
			norm_file = normalize_file(orig_file, separators)
			include, index = self._backend.match_file(norm_file)
			yield CheckResult(orig_file, include, index)

	def check_tree_files(
		self,
		root: StrPath,
		on_error: Optional[Callable[[OSError], None]] = None,
		follow_links: Optional[bool] = None,
	) -> Iterator[CheckResult[str]]:
		"""
		Walks the specified root path for all files and checks them against this
		path-spec.

		*root* (:class:`str` or :class:`os.PathLike`) is the root directory to
		search for files.

		*on_error* (:class:`~collections.abc.Callable` or :data:`None`) optionally
		is the error handler for file-system exceptions. It will be called with the
		exception (:exc:`OSError`). Reraise the exception to abort the walk. Default
		is :data:`None` to ignore file-system exceptions.

		*follow_links* (:class:`bool` or :data:`None`) optionally is whether to walk
		symbolic links that resolve to directories. Default is :data:`None` for
		:data:`True`.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns an :class:`~collections.abc.Iterator` yielding each file check
		result (:class:`.CheckResult`).
		"""
		files = util.iter_tree_files(root, on_error=on_error, follow_links=follow_links)
		yield from self.check_files(files)

	@classmethod
	def from_lines(
		cls: type[Self],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern]],
		lines: Iterable[AnyStr],
		*,
		backend: Union[BackendNamesHint, str, None] = None,
		_test_backend_factory: Optional[Callable[[Sequence[Pattern]], _Backend]] = None,
	) -> Self:
		"""
		Compiles the pattern lines.

		*pattern_factory* can be either the name of a registered pattern factory
		(:class:`str`), or a :class:`~collections.abc.Callable` used to compile
		patterns. It must accept an uncompiled pattern (:class:`str`) and return the
		compiled pattern (:class:`.Pattern`).

		*lines* (:class:`~collections.abc.Iterable`) yields each uncompiled pattern
		(:class:`str`). This simply has to yield each line so that it can be a
		:class:`io.TextIOBase` (e.g., from :func:`open` or :class:`io.StringIO`) or
		the result from :meth:`str.splitlines`.

		*backend* (:class:`str` or :data:`None`) is the pattern (or regular
		expression) matching backend to use. Default is :data:`None` for "best" to
		use the best available backend. Priority of backends is: "re2", "hyperscan",
		"simple". The "simple" backend is always available.

		Returns the :class:`PathSpec` instance.
		"""
		if isinstance(pattern_factory, str):
			pattern_factory = util.lookup_pattern(pattern_factory)

		if not callable(pattern_factory):
			raise TypeError(f"pattern_factory:{pattern_factory!r} is not callable.")

		if not _is_iterable(lines):
			raise TypeError(f"lines:{lines!r} is not an iterable.")

		patterns = [pattern_factory(line) for line in lines if line]
		return cls(patterns, backend=backend, _test_backend_factory=_test_backend_factory)

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

		Returns the matcher (:class:`._Backend`).
		"""
		return make_pathspec_backend(name, patterns)

	def match_entries(
		self,
		entries: Iterable[TreeEntry],
		separators: Optional[Collection[str]] = None,
		*,
		negate: Optional[bool] = None,
	) -> Iterator[TreeEntry]:
		"""
		Matches the entries to this path-spec.

		*entries* (:class:`~collections.abc.Iterable` of :class:`.TreeEntry`)
		contains the entries to be matched against :attr:`self.patterns <.PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`.normalize_file` for more information.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns the matched entries (:class:`~collections.abc.Iterator` of
		:class:`.TreeEntry`).
		"""
		if not _is_iterable(entries):
			raise TypeError(f"entries:{entries!r} is not an iterable.")

		for entry in entries:
			norm_file = normalize_file(entry.path, separators)
			include, _index = self._backend.match_file(norm_file)

			if negate:
				include = not include

			if include:
				yield entry

	def match_file(
		self,
		file: StrPath,
		separators: Optional[Collection[str]] = None,
	) -> bool:
		"""
		Matches the file to this path-spec.

		*file* (:class:`str` or :class:`os.PathLike`) is the file path to be matched
		against :attr:`self.patterns <.PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`)
		optionally contains the path separators to normalize. See
		:func:`.normalize_file` for more information.

		Returns :data:`True` if *file* matched; otherwise, :data:`False`.
		"""
		norm_file = normalize_file(file, separators)
		include, _index = self._backend.match_file(norm_file)
		return bool(include)

	def match_files(
		self,
		files: Iterable[StrPath],
		separators: Optional[Collection[str]] = None,
		*,
		negate: Optional[bool] = None,
	) -> Iterator[StrPath]:
		"""
		Matches the files to this path-spec.

		*files* (:class:`~collections.abc.Iterable` of :class:`str` or
		:class:`os.PathLike`) contains the file paths to be matched against
		:attr:`self.patterns <.PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`.normalize_file` for more information.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns the matched files (:class:`~collections.abc.Iterator` of
		:class:`str` or :class:`os.PathLike`).
		"""
		if not _is_iterable(files):
			raise TypeError(f"files:{files!r} is not an iterable.")

		for orig_file in files:
			norm_file = normalize_file(orig_file, separators)
			include, _index = self._backend.match_file(norm_file)

			if negate:
				include = not include

			if include:
				yield orig_file

	def match_tree_entries(
		self,
		root: StrPath,
		on_error: Optional[Callable[[OSError], None]] = None,
		follow_links: Optional[bool] = None,
		*,
		negate: Optional[bool] = None,
	) -> Iterator[TreeEntry]:
		"""
		Walks the specified root path for all files and matches them to this
		path-spec.

		*root* (:class:`str` or :class:`os.PathLike`) is the root directory to
		search.

		*on_error* (:class:`~collections.abc.Callable` or :data:`None`) optionally
		is the error handler for file-system exceptions. It will be called with the
		exception (:exc:`OSError`). Reraise the exception to abort the walk. Default
		is :data:`None` to ignore file-system exceptions.

		*follow_links* (:class:`bool` or :data:`None`) optionally is whether to walk
		symbolic links that resolve to directories. Default is :data:`None` for
		:data:`True`.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns the matched files (:class:`~collections.abc.Iterator` of
		:class:`.TreeEntry`).
		"""
		entries = util.iter_tree_entries(root, on_error=on_error, follow_links=follow_links)
		yield from self.match_entries(entries, negate=negate)

	# NOTICE: The deprecation warning was only added in 1.0.0 (from 2026-01-05).
	@deprecated((
		"PathSpec.match_tree() is deprecated. Use .match_tree_files() instead."
	))
	def match_tree(self, *args, **kw) -> Iterator[str]:
		"""
		.. version-deprecated:: 0.3.2
			This is an alias for the :meth:`self.match_tree_files <.PathSpec.match_tree_files>`
			method.
		"""
		return self.match_tree_files(*args, **kw)

	def match_tree_files(
		self,
		root: StrPath,
		on_error: Optional[Callable[[OSError], None]] = None,
		follow_links: Optional[bool] = None,
		*,
		negate: Optional[bool] = None,
	) -> Iterator[str]:
		"""
		Walks the specified root path for all files and matches them to this
		path-spec.

		*root* (:class:`str` or :class:`os.PathLike`) is the root directory to
		search for files.

		*on_error* (:class:`~collections.abc.Callable` or :data:`None`) optionally
		is the error handler for file-system exceptions. It will be called with the
		exception (:exc:`OSError`). Reraise the exception to abort the walk. Default
		is :data:`None` to ignore file-system exceptions.

		*follow_links* (:class:`bool` or :data:`None`) optionally is whether to walk
		symbolic links that resolve to directories. Default is :data:`None` for
		:data:`True`.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns the matched files (:class:`~collections.abc.Iterable` of :class:`str`).
		"""
		files = util.iter_tree_files(root, on_error=on_error, follow_links=follow_links)
		yield from self.match_files(files, negate=negate)
