"""Operating system-related utility functions for Sphinx."""

from __future__ import annotations

import contextlib
import filecmp
import os
import re
import shutil
import sys
import unicodedata
from io import StringIO
from os import path
from typing import TYPE_CHECKING, Any

from sphinx.deprecation import _deprecation_warning

if TYPE_CHECKING:
    from collections.abc import Iterator

# SEP separates path elements in the canonical file names
#
# Define SEP as a manifest constant, not so much because we expect it to change
# in the future as to avoid the suspicion that a stray "/" in the code is a
# hangover from more *nix-oriented origins.
SEP = "/"


def os_path(canonical_path: str, /) -> str:
    return canonical_path.replace(SEP, path.sep)


def canon_path(native_path: str | os.PathLike[str], /) -> str:
    """Return path in OS-independent form"""
    return os.fspath(native_path).replace(path.sep, SEP)


def path_stabilize(filepath: str | os.PathLike[str], /) -> str:
    "Normalize path separator and unicode string"
    new_path = canon_path(filepath)
    return unicodedata.normalize('NFC', new_path)


def relative_uri(base: str, to: str) -> str:
    """Return a relative URL from ``base`` to ``to``."""
    if to.startswith(SEP):
        return to
    b2 = base.split('#')[0].split(SEP)
    t2 = to.split('#')[0].split(SEP)
    # remove common segments (except the last segment)
    for x, y in zip(b2[:-1], t2[:-1]):
        if x != y:
            break
        b2.pop(0)
        t2.pop(0)
    if b2 == t2:
        # Special case: relative_uri('f/index.html','f/index.html')
        # returns '', not 'index.html'
        return ''
    if len(b2) == 1 and t2 == ['']:
        # Special case: relative_uri('f/index.html','f/') should
        # return './', not ''
        return '.' + SEP
    return ('..' + SEP) * (len(b2) - 1) + SEP.join(t2)


def ensuredir(file: str | os.PathLike[str]) -> None:
    """Ensure that a path exists."""
    os.makedirs(file, exist_ok=True)


def mtimes_of_files(dirnames: list[str], suffix: str) -> Iterator[float]:
    for dirname in dirnames:
        for root, _dirs, files in os.walk(dirname):
            for sfile in files:
                if sfile.endswith(suffix):
                    with contextlib.suppress(OSError):
                        yield path.getmtime(path.join(root, sfile))


def copytimes(source: str | os.PathLike[str], dest: str | os.PathLike[str]) -> None:
    """Copy a file's modification times."""
    st = os.stat(source)
    if hasattr(os, 'utime'):
        os.utime(dest, (st.st_atime, st.st_mtime))


def copyfile(source: str | os.PathLike[str], dest: str | os.PathLike[str]) -> None:
    """Copy a file and its modification times, if possible.

    Note: ``copyfile`` skips copying if the file has not been changed"""
    if not path.exists(dest) or not filecmp.cmp(source, dest):
        shutil.copyfile(source, dest)
        with contextlib.suppress(OSError):
            # don't do full copystat because the source may be read-only
            copytimes(source, dest)


no_fn_re = re.compile(r'[^a-zA-Z0-9_-]')
project_suffix_re = re.compile(' Documentation$')


def make_filename(string: str) -> str:
    return no_fn_re.sub('', string) or 'sphinx'


def make_filename_from_project(project: str) -> str:
    return make_filename(project_suffix_re.sub('', project)).lower()


def relpath(path: str | os.PathLike[str],
            start: str | os.PathLike[str] | None = os.curdir) -> str:
    """Return a relative filepath to *path* either from the current directory or
    from an optional *start* directory.

    This is an alternative of ``os.path.relpath()``.  This returns original path
    if *path* and *start* are on different drives (for Windows platform).
    """
    try:
        return os.path.relpath(path, start)
    except ValueError:
        return str(path)


safe_relpath = relpath  # for compatibility
fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()


abspath = path.abspath


class _chdir:
    """Remove this fall-back once support for Python 3.10 is removed."""
    def __init__(self, target_dir: str, /):
        self.path = target_dir
        self._dirs: list[str] = []

    def __enter__(self):
        self._dirs.append(os.getcwd())
        os.chdir(self.path)

    def __exit__(self, _exc_type, _exc_value, _traceback, /):
        os.chdir(self._dirs.pop())


@contextlib.contextmanager
def cd(target_dir: str) -> Iterator[None]:
    if sys.version_info[:2] >= (3, 11):
        _deprecation_warning(__name__, 'cd', 'contextlib.chdir', remove=(8, 0))
    with _chdir(target_dir):
        yield


class FileAvoidWrite:
    """File-like object that buffers output and only writes if content changed.

    Use this class like when writing to a file to avoid touching the original
    file if the content hasn't changed. This is useful in scenarios where file
    mtime is used to invalidate caches or trigger new behavior.

    When writing to this file handle, all writes are buffered until the object
    is closed.

    Objects can be used as context managers.
    """
    def __init__(self, path: str) -> None:
        self._path = path
        self._io: StringIO | None = None

    def write(self, data: str) -> None:
        if not self._io:
            self._io = StringIO()
        self._io.write(data)

    def close(self) -> None:
        """Stop accepting writes and write file, if needed."""
        if not self._io:
            msg = 'FileAvoidWrite does not support empty files.'
            raise Exception(msg)

        buf = self.getvalue()
        self._io.close()

        try:
            with open(self._path, encoding='utf-8') as old_f:
                old_content = old_f.read()
                if old_content == buf:
                    return
        except OSError:
            pass

        with open(self._path, 'w', encoding='utf-8') as f:
            f.write(buf)

    def __enter__(self) -> FileAvoidWrite:
        return self

    def __exit__(
        self, exc_type: type[Exception], exc_value: Exception, traceback: Any,
    ) -> bool:
        self.close()
        return True

    def __getattr__(self, name: str) -> Any:
        # Proxy to _io instance.
        if not self._io:
            msg = 'Must write to FileAvoidWrite before other methods can be used'
            raise Exception(msg)

        return getattr(self._io, name)


def rmtree(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
