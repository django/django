"""
The *pathspec* package provides pattern matching for file paths. So far this
only includes Git's *gitignore* patterns.

The following classes are imported and made available from the root of the
`pathspec` package:

-	:class:`pathspec.gitignore.GitIgnoreSpec`

-	:class:`pathspec.pathspec.PathSpec`

-	:class:`pathspec.pattern.Pattern`

-	:class:`pathspec.pattern.RegexPattern`

-	:class:`pathspec.util.RecursionError`

The following functions are also imported:

-	:func:`pathspec.util.lookup_pattern`

The following deprecated functions are also imported to maintain backward
compatibility:

-	:func:`pathspec.util.iter_tree`

-	:func:`pathspec.util.match_files`
"""

from .gitignore import (
	GitIgnoreSpec)
from .pathspec import (
	PathSpec)
from .pattern import (
	Pattern,
	RegexPattern)
from .util import (
	RecursionError,
	iter_tree,  # Deprecated since 0.10.0.
	lookup_pattern,
	match_files)  # Deprecated since 0.10.0.

from ._meta import (
	__author__,
	__copyright__,
	__credits__,
	__license__)
from ._version import (
	__version__)

# Load pattern implementations.
from . import patterns

# Declare private imports as part of the public interface. Deprecated imports
# are deliberately excluded.
__all__ = [
	'GitIgnoreSpec',
	'PathSpec',
	'Pattern',
	'RecursionError',
	'RegexPattern',
	'__author__',
	'__copyright__',
	'__credits__',
	'__license__',
	'__version__',
	'lookup_pattern',
]
