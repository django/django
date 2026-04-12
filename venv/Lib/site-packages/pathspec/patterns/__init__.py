"""
The *pathspec.patterns* package contains the pattern matching implementations.
"""

# Load pattern implementations.
from .gitignore import basic as _
from .gitignore import spec as _

# DEPRECATED: Deprecated since 0.11.0 (from 2023-01-24). Expose the
# GitWildMatchPattern class in this module for backward compatibility with
# 0.5.0 (from 2016-08-22).
from .gitwildmatch import GitWildMatchPattern
