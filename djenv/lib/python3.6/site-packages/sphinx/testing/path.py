# -*- coding: utf-8 -*-
"""
    sphinx.testing.path
    ~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import os
import shutil
import sys
from io import open

from six import PY2, text_type

if False:
    # For type annotation
    from typing import Any, Callable, IO, List  # NOQA


FILESYSTEMENCODING = sys.getfilesystemencoding() or sys.getdefaultencoding()


class path(text_type):
    """
    Represents a path which behaves like a string.
    """
    if PY2:
        def __new__(cls, s, encoding=FILESYSTEMENCODING, errors='strict'):
            # type: (unicode, unicode, unicode) -> path
            if isinstance(s, str):
                s = s.decode(encoding, errors)
                return text_type.__new__(cls, s)  # type: ignore
            return text_type.__new__(cls, s)  # type: ignore

    @property
    def parent(self):
        # type: () -> path
        """
        The name of the directory the file or directory is in.
        """
        return self.__class__(os.path.dirname(self))

    def basename(self):
        # type: () -> unicode
        return os.path.basename(self)

    def abspath(self):
        # type: () -> path
        """
        Returns the absolute path.
        """
        return self.__class__(os.path.abspath(self))

    def isabs(self):
        # type: () -> bool
        """
        Returns ``True`` if the path is absolute.
        """
        return os.path.isabs(self)

    def isdir(self):
        # type: () -> bool
        """
        Returns ``True`` if the path is a directory.
        """
        return os.path.isdir(self)

    def isfile(self):
        # type: () -> bool
        """
        Returns ``True`` if the path is a file.
        """
        return os.path.isfile(self)

    def islink(self):
        # type: () -> bool
        """
        Returns ``True`` if the path is a symbolic link.
        """
        return os.path.islink(self)

    def ismount(self):
        # type: () -> bool
        """
        Returns ``True`` if the path is a mount point.
        """
        return os.path.ismount(self)

    def rmtree(self, ignore_errors=False, onerror=None):
        # type: (bool, Callable) -> None
        """
        Removes the file or directory and any files or directories it may
        contain.

        :param ignore_errors:
            If ``True`` errors are silently ignored, otherwise an exception
            is raised in case an error occurs.

        :param onerror:
            A callback which gets called with the arguments `func`, `path` and
            `exc_info`. `func` is one of :func:`os.listdir`, :func:`os.remove`
            or :func:`os.rmdir`. `path` is the argument to the function which
            caused it to fail and `exc_info` is a tuple as returned by
            :func:`sys.exc_info`.
        """
        shutil.rmtree(self, ignore_errors=ignore_errors, onerror=onerror)

    def copytree(self, destination, symlinks=False):
        # type: (unicode, bool) -> None
        """
        Recursively copy a directory to the given `destination`. If the given
        `destination` does not exist it will be created.

        :param symlinks:
            If ``True`` symbolic links in the source tree result in symbolic
            links in the destination tree otherwise the contents of the files
            pointed to by the symbolic links are copied.
        """
        shutil.copytree(self, destination, symlinks=symlinks)

    def movetree(self, destination):
        # type: (unicode) -> None
        """
        Recursively move the file or directory to the given `destination`
        similar to the  Unix "mv" command.

        If the `destination` is a file it may be overwritten depending on the
        :func:`os.rename` semantics.
        """
        shutil.move(self, destination)

    move = movetree

    def unlink(self):
        # type: () -> None
        """
        Removes a file.
        """
        os.unlink(self)

    def stat(self):
        # type: () -> Any
        """
        Returns a stat of the file.
        """
        return os.stat(self)

    def utime(self, arg):
        # type: (Any) -> None
        os.utime(self, arg)

    def open(self, mode='r', **kwargs):
        # type: (unicode, Any) -> IO
        return open(self, mode, **kwargs)

    def write_text(self, text, encoding='utf-8', **kwargs):
        # type: (unicode, unicode, Any) -> None
        """
        Writes the given `text` to the file.
        """
        if isinstance(text, bytes):
            text = text.decode(encoding)
        with open(self, 'w', encoding=encoding, **kwargs) as f:
            f.write(text)

    def text(self, encoding='utf-8', **kwargs):
        # type: (unicode, Any) -> unicode
        """
        Returns the text in the file.
        """
        mode = 'rU' if PY2 else 'r'
        with open(self, mode=mode, encoding=encoding, **kwargs) as f:
            return f.read()

    def bytes(self):
        # type: () -> str
        """
        Returns the bytes in the file.
        """
        with open(self, mode='rb') as f:
            return f.read()

    def write_bytes(self, bytes, append=False):
        # type: (str, bool) -> None
        """
        Writes the given `bytes` to the file.

        :param append:
            If ``True`` given `bytes` are added at the end of the file.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        with open(self, mode=mode) as f:
            f.write(bytes)

    def exists(self):
        # type: () -> bool
        """
        Returns ``True`` if the path exist.
        """
        return os.path.exists(self)

    def lexists(self):
        # type: () -> bool
        """
        Returns ``True`` if the path exists unless it is a broken symbolic
        link.
        """
        return os.path.lexists(self)

    def makedirs(self, mode=0o777):
        # type: (int) -> None
        """
        Recursively create directories.
        """
        os.makedirs(self, mode)

    def joinpath(self, *args):
        # type: (Any) -> path
        """
        Joins the path with the argument given and returns the result.
        """
        return self.__class__(os.path.join(self, *map(self.__class__, args)))

    def listdir(self):
        # type: () -> List[unicode]
        return os.listdir(self)

    __div__ = __truediv__ = joinpath

    def __repr__(self):
        # type: () -> str
        return '%s(%s)' % (self.__class__.__name__, text_type.__repr__(self))
