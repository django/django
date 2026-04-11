"""
The *pathspec.patterns.gitignore* package provides the *gitignore*
implementations.

The following classes are imported and made available from this package:

- :class:`pathspec.patterns.gitignore.base.GitIgnorePatternError`
"""

# Expose the GitIgnorePatternError for convenience.
from .base import (
	GitIgnorePatternError)

# Declare imports as part of the public interface.
__all__ = [
	'GitIgnorePatternError',
]
