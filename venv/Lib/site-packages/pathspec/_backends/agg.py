"""
This module provides aggregated private data and utilities functions about the
available backends.

WARNING: The *pathspec._backends* package is not part of the public API. Its
contents and structure are likely to change.
"""

from collections.abc import (
	Sequence)
from typing import (
	cast)

from pathspec.backend import (
	BackendNamesHint,
	_Backend)
from pathspec.pattern import (
	Pattern,
	RegexPattern)

from .hyperscan.base import (
	hyperscan_error)
from .hyperscan.gitignore import (
	HyperscanGiBackend)
from .hyperscan.pathspec import (
	HyperscanPsBackend)
from .re2.base import (
	re2_error)
from .re2.gitignore import (
	Re2GiBackend)
from .re2.pathspec import (
	Re2PsBackend)
from .simple.gitignore import (
	SimpleGiBackend)
from .simple.pathspec import (
	SimplePsBackend)

_BEST_BACKEND: BackendNamesHint
"""
The best available backend.
"""

if re2_error is None:
	_BEST_BACKEND = 're2'
elif hyperscan_error is None:
	_BEST_BACKEND = 'hyperscan'
else:
	_BEST_BACKEND = 'simple'


def make_gitignore_backend(
	name: BackendNamesHint,
	patterns: Sequence[Pattern],
) -> _Backend:
	"""
	Create the specified backend with the supplied patterns for
	:class:`~pathspec.gitignore.GitIgnoreSpec`.

	*name* (:class:`str`) is the name of the backend.

	*patterns* (:class:`.Iterable` of :class:`.Pattern`) contains the compiled
	patterns.

	Returns the backend (:class:`._Backend`).
	"""
	if name == 'best':
		name = _BEST_BACKEND

	if name == 'hyperscan':
		return HyperscanGiBackend(cast(Sequence[RegexPattern], patterns))
	elif name == 're2':
		return Re2GiBackend(cast(Sequence[RegexPattern], patterns))
	elif name == 'simple':
		return SimpleGiBackend(cast(Sequence[RegexPattern], patterns))
	else:
		raise ValueError(f"Backend {name=!r} is invalid.")


def make_pathspec_backend(
	name: BackendNamesHint,
	patterns: Sequence[Pattern],
) -> _Backend:
	"""
	Create the specified backend with the supplied patterns for
	:class:`~pathspec.pathspec.PathSpec`.

	*name* (:class:`str`) is the name of the backend.

	*patterns* (:class:`Iterable` of :class:`Pattern`) contains the compiled
	patterns.

	Returns the backend (:class:`._Backend`).
	"""
	if name == 'best':
		name = _BEST_BACKEND

	if name == 'hyperscan':
		return HyperscanPsBackend(cast(Sequence[RegexPattern], patterns))
	elif name == 're2':
		return Re2PsBackend(cast(Sequence[RegexPattern], patterns))
	elif name == 'simple':
		return SimplePsBackend(patterns)
	else:
		raise ValueError(f"Backend {name=!r} is invalid.")
