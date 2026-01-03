"""
This module provides an object oriented interface for pattern matching of files.
"""

from collections.abc import (
	Collection as CollectionType)
from itertools import (
	zip_longest)
from typing import (
	AnyStr,
	Callable,  # Replaced by `collections.abc.Callable` in 3.9.
	Collection,  # Replaced by `collections.abc.Collection` in 3.9.
	Iterable,  # Replaced by `collections.abc.Iterable` in 3.9.
	Iterator,  # Replaced by `collections.abc.Iterator` in 3.9.
	Optional,  # Replaced by `X | None` in 3.10.
	Type,  # Replaced by `type` in 3.9.
	TypeVar,
	Union)  # Replaced by `X | Y` in 3.10.

from . import util
from .pattern import (
	Pattern)
from .util import (
	CheckResult,
	StrPath,
	TStrPath,
	TreeEntry,
	_filter_check_patterns,
	_is_iterable,
	normalize_file)

Self = TypeVar("Self", bound="PathSpec")
"""
:class:`PathSpec` self type hint to support Python v<3.11 using PEP 673
recommendation.
"""


class PathSpec(object):
	"""
	The :class:`PathSpec` class is a wrapper around a list of compiled
	:class:`.Pattern` instances.
	"""

	def __init__(self, patterns: Iterable[Pattern]) -> None:
		"""
		Initializes the :class:`PathSpec` instance.

		*patterns* (:class:`~collections.abc.Collection` or :class:`~collections.abc.Iterable`)
		yields each compiled pattern (:class:`.Pattern`).
		"""
		if not isinstance(patterns, CollectionType):
			patterns = list(patterns)

		self.patterns: Collection[Pattern] = patterns
		"""
		*patterns* (:class:`~collections.abc.Collection` of :class:`.Pattern`)
		contains the compiled patterns.
		"""

	def __eq__(self, other: object) -> bool:
		"""
		Tests the equality of this path-spec with *other* (:class:`PathSpec`)
		by comparing their :attr:`~PathSpec.patterns` attributes.
		"""
		if isinstance(other, PathSpec):
			paired_patterns = zip_longest(self.patterns, other.patterns)
			return all(a == b for a, b in paired_patterns)
		else:
			return NotImplemented

	def __len__(self) -> int:
		"""
		Returns the number of compiled patterns this path-spec contains
		(:class:`int`).
		"""
		return len(self.patterns)

	def __add__(self: Self, other: "PathSpec") -> Self:
		"""
		Combines the :attr:`Pathspec.patterns` patterns from two
		:class:`PathSpec` instances.
		"""
		if isinstance(other, PathSpec):
			return self.__class__(self.patterns + other.patterns)
		else:
			return NotImplemented

	def __iadd__(self: Self, other: "PathSpec") -> Self:
		"""
		Adds the :attr:`Pathspec.patterns` patterns from one :class:`PathSpec`
		instance to this instance.
		"""
		if isinstance(other, PathSpec):
			self.patterns += other.patterns
			return self
		else:
			return NotImplemented

	def check_file(
		self,
		file: TStrPath,
		separators: Optional[Collection[str]] = None,
	) -> CheckResult[TStrPath]:
		"""
		Check the files against this path-spec.

		*file* (:class:`str` or :class:`os.PathLike`) is the file path to be
		matched against :attr:`self.patterns <PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`~pathspec.util.normalize_file` for more information.

		Returns the file check result (:class:`~pathspec.util.CheckResult`).
		"""
		norm_file = normalize_file(file, separators)
		include, index = self._match_file(enumerate(self.patterns), norm_file)
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
		:attr:`self.patterns <PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`~pathspec.util.normalize_file` for more information.

		Returns an :class:`~collections.abc.Iterator` yielding each file check
		result (:class:`~pathspec.util.CheckResult`).
		"""
		if not _is_iterable(files):
			raise TypeError(f"files:{files!r} is not an iterable.")

		use_patterns = _filter_check_patterns(self.patterns)
		for orig_file in files:
			norm_file = normalize_file(orig_file, separators)
			include, index = self._match_file(use_patterns, norm_file)
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
		result (:class:`~pathspec.util.CheckResult`).
		"""
		files = util.iter_tree_files(root, on_error=on_error, follow_links=follow_links)
		yield from self.check_files(files)

	@classmethod
	def from_lines(
		cls: Type[Self],
		pattern_factory: Union[str, Callable[[AnyStr], Pattern]],
		lines: Iterable[AnyStr],
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

		Returns the :class:`PathSpec` instance.
		"""
		if isinstance(pattern_factory, str):
			pattern_factory = util.lookup_pattern(pattern_factory)

		if not callable(pattern_factory):
			raise TypeError(f"pattern_factory:{pattern_factory!r} is not callable.")

		if not _is_iterable(lines):
			raise TypeError(f"lines:{lines!r} is not an iterable.")

		patterns = [pattern_factory(line) for line in lines if line]
		return cls(patterns)

	def match_entries(
		self,
		entries: Iterable[TreeEntry],
		separators: Optional[Collection[str]] = None,
		*,
		negate: Optional[bool] = None,
	) -> Iterator[TreeEntry]:
		"""
		Matches the entries to this path-spec.

		*entries* (:class:`~collections.abc.Iterable` of :class:`~pathspec.util.TreeEntry`)
		contains the entries to be matched against :attr:`self.patterns <PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`~pathspec.util.normalize_file` for more information.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns the matched entries (:class:`~collections.abc.Iterator` of
		:class:`~pathspec.util.TreeEntry`).
		"""
		if not _is_iterable(entries):
			raise TypeError(f"entries:{entries!r} is not an iterable.")

		use_patterns = _filter_check_patterns(self.patterns)
		for entry in entries:
			norm_file = normalize_file(entry.path, separators)
			include, _index = self._match_file(use_patterns, norm_file)

			if negate:
				include = not include

			if include:
				yield entry

	_match_file = staticmethod(util.check_match_file)
	"""
	Match files using the `check_match_file()` utility function. Subclasses may
	override this method as an instance method. It does not have to be a static
	method. The signature for this method is subject to change.
	"""

	def match_file(
		self,
		file: StrPath,
		separators: Optional[Collection[str]] = None,
	) -> bool:
		"""
		Matches the file to this path-spec.

		*file* (:class:`str` or :class:`os.PathLike`) is the file path to be
		matched against :attr:`self.patterns <PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`)
		optionally contains the path separators to normalize. See
		:func:`~pathspec.util.normalize_file` for more information.

		Returns :data:`True` if *file* matched; otherwise, :data:`False`.
		"""
		norm_file = normalize_file(file, separators)
		include, _index = self._match_file(enumerate(self.patterns), norm_file)
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
		:attr:`self.patterns <PathSpec.patterns>`.

		*separators* (:class:`~collections.abc.Collection` of :class:`str`; or
		:data:`None`) optionally contains the path separators to normalize. See
		:func:`~pathspec.util.normalize_file` for more information.

		*negate* (:class:`bool` or :data:`None`) is whether to negate the match
		results of the patterns. If :data:`True`, a pattern matching a file will
		exclude the file rather than include it. Default is :data:`None` for
		:data:`False`.

		Returns the matched files (:class:`~collections.abc.Iterator` of
		:class:`str` or :class:`os.PathLike`).
		"""
		if not _is_iterable(files):
			raise TypeError(f"files:{files!r} is not an iterable.")

		use_patterns = _filter_check_patterns(self.patterns)
		for orig_file in files:
			norm_file = normalize_file(orig_file, separators)
			include, _index = self._match_file(use_patterns, norm_file)

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

		Returns the matched files (:class:`~collections.abc.Iterable` of
		:class:`str`).
		"""
		files = util.iter_tree_files(root, on_error=on_error, follow_links=follow_links)
		yield from self.match_files(files, negate=negate)

	# Alias `match_tree_files()` as `match_tree()` for backward compatibility
	# before v0.3.2.
	match_tree = match_tree_files
