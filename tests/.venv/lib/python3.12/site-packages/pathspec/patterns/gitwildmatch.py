"""
.. version-deprecated: 1.0.0
	This module is superseded by :module:`pathspec.patterns.gitignore`.
"""

from pathspec import util
from pathspec._typing import (
	deprecated,  # Added in 3.13.
	override)  # Added in 3.12.

from .gitignore.spec import (
	GitIgnoreSpecPattern)

# DEPRECATED: Deprecated since version 1.0.0. Expose GitWildMatchPatternError
# in this module for backward compatibility.
from .gitignore import (
	GitIgnorePatternError as GitWildMatchPatternError)


class GitWildMatchPattern(GitIgnoreSpecPattern):
	"""
	.. version-deprecated:: 1.0.0
		This class is superseded by :class:`GitIgnoreSpecPattern` and
		:class:`~pathspec.patterns.gitignore.basic.GitIgnoreBasicPattern`.
	"""

	@deprecated((
		"GitWildMatchPattern ('gitwildmatch') is deprecated. Use 'gitignore' for "
		"GitIgnoreBasicPattern or GitIgnoreSpecPattern instead."
	))
	def __init__(self, *args, **kw) -> None:
		"""
		Warn about deprecation.
		"""
		super().__init__(*args, **kw)

	@override
	@classmethod
	@deprecated((
		"GitWildMatchPattern ('gitwildmatch') is deprecated. Use 'gitignore' for "
		"GitIgnoreBasicPattern or GitIgnoreSpecPattern instead."
	))
	def pattern_to_regex(cls, *args, **kw):
		"""
		Warn about deprecation.
		"""
		return super().pattern_to_regex(*args, **kw)


# DEPRECATED: Deprecated since version 1.0.0. Register GitWildMatchPattern as
# "gitwildmatch" for backward compatibility.
util.register_pattern('gitwildmatch', GitWildMatchPattern)
