"""
This module provides common classes for the gitignore patterns.
"""

import re

from pathspec.pattern import (
	RegexPattern)
from pathspec._typing import (
	AnyStr)  # Removed in 3.18.

_BYTES_ENCODING = 'latin1'
"""
The encoding to use when parsing a byte string pattern.
"""


class _GitIgnoreBasePattern(RegexPattern):
	"""
	.. warning:: This class is not part of the public API. It is subject to
		change.

	The :class:`_GitIgnoreBasePattern` class is the base implementation for a
	compiled gitignore pattern.
	"""

	# Keep the dict-less class hierarchy.
	__slots__ = ()

	@staticmethod
	def escape(s: AnyStr) -> AnyStr:
		"""
		Escape special characters in the given string.

		*s* (:class:`str` or :class:`bytes`) a filename or a string that you want to
		escape, usually before adding it to a ".gitignore".

		Returns the escaped string (:class:`str` or :class:`bytes`).
		"""
		if isinstance(s, str):
			return_type = str
			string = s
		elif isinstance(s, bytes):
			return_type = bytes
			string = s.decode(_BYTES_ENCODING)
		else:
			raise TypeError(f"s:{s!r} is not a unicode or byte string.")

		# Reference: https://git-scm.com/docs/gitignore#_pattern_format
		out_string = ''.join((f"\\{x}" if x in '[]!*#?' else x) for x in string)

		if return_type is bytes:
			return out_string.encode(_BYTES_ENCODING)
		else:
			return out_string

	@staticmethod
	def _translate_segment_glob(pattern: str) -> str:
		"""
		Translates the glob pattern to a regular expression. This is used in the
		constructor to translate a path segment glob pattern to its corresponding
		regular expression.

		*pattern* (:class:`str`) is the glob pattern.

		Returns the regular expression (:class:`str`).
		"""
		# NOTE: This is derived from `fnmatch.translate()` and is similar to the
		# POSIX function `fnmatch()` with the `FNM_PATHNAME` flag set.

		escape = False
		regex = ''
		i, end = 0, len(pattern)
		while i < end:
			# Get next character.
			char = pattern[i]
			i += 1

			if escape:
				# Escape the character.
				escape = False
				regex += re.escape(char)

			elif char == '\\':
				# Escape character, escape next character.
				escape = True

			elif char == '*':
				# Multi-character wildcard. Match any string (except slashes), including
				# an empty string.
				regex += '[^/]*'

			elif char == '?':
				# Single-character wildcard. Match any single character (except a
				# slash).
				regex += '[^/]'

			elif char == '[':
				# Bracket expression wildcard. Except for the beginning exclamation
				# mark, the whole bracket expression can be used directly as regex, but
				# we have to find where the expression ends.
				# - "[][!]" matches ']', '[' and '!'.
				# - "[]-]" matches ']' and '-'.
				# - "[!]a-]" matches any character except ']', 'a' and '-'.
				j = i

				# Pass bracket expression negation.
				if j < end and (pattern[j] == '!' or pattern[j] == '^'):
					j += 1

				# Pass first closing bracket if it is at the beginning of the
				# expression.
				if j < end and pattern[j] == ']':
					j += 1

				# Find closing bracket. Stop once we reach the end or find it.
				while j < end and pattern[j] != ']':
					j += 1

				if j < end:
					# Found end of bracket expression. Increment j to be one past the
					# closing bracket:
					#
					#  [...]
					#   ^   ^
					#   i   j
					#
					j += 1
					expr = '['

					if pattern[i] == '!':
						# Bracket expression needs to be negated.
						expr += '^'
						i += 1
					elif pattern[i] == '^':
						# POSIX declares that the regex bracket expression negation "[^...]"
						# is undefined in a glob pattern. Python's `fnmatch.translate()`
						# escapes the caret ('^') as a literal. Git supports the using a
						# caret for negation. Maintain consistency with Git because that is
						# the expected behavior.
						expr += '^'
						i += 1

					# Build regex bracket expression. Escape slashes so they are treated
					# as literal slashes by regex as defined by POSIX.
					expr += pattern[i:j].replace('\\', '\\\\')

					# Add regex bracket expression to regex result.
					regex += expr

					# Set i to one past the closing bracket.
					i = j

				else:
					# Failed to find closing bracket, treat opening bracket as a bracket
					# literal instead of as an expression.
					regex += '\\['

			else:
				# Regular character, escape it for regex.
				regex += re.escape(char)

		if escape:
			raise ValueError((
				f"Escape character found with no next character to escape: {pattern!r}"
			))  # ValueError

		return regex


class GitIgnorePatternError(ValueError):
	"""
	The :class:`GitIgnorePatternError` class indicates an invalid gitignore
	pattern.
	"""
	pass
