import os
import sys
from typing import Union

if sys.version_info >= (3, 9):
    StrPath = Union[str, os.PathLike[str]]  #  Same as _typeshed.StrPath
else:
    StrPath = Union[str, os.PathLike]


def ensure_directory(path):
    """Ensure that the parent directory of `path` exists"""
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)


def same_path(p1: StrPath, p2: StrPath) -> bool:
    """Differs from os.path.samefile because it does not require paths to exist.
    Purely string based (no comparison between i-nodes).
    >>> same_path("a/b", "./a/b")
    True
    >>> same_path("a/b", "a/./b")
    True
    >>> same_path("a/b", "././a/b")
    True
    >>> same_path("a/b", "./a/b/c/..")
    True
    >>> same_path("a/b", "../a/b/c")
    False
    >>> same_path("a", "a/b")
    False
    """
    return normpath(p1) == normpath(p2)


def normpath(filename: StrPath) -> str:
    """Normalize a file/dir name for comparison purposes."""
    # See pkg_resources.normalize_path for notes about cygwin
    file = os.path.abspath(filename) if sys.platform == 'cygwin' else filename
    return os.path.normcase(os.path.realpath(os.path.normpath(file)))
