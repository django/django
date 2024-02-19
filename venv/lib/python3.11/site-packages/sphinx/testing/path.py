from __future__ import annotations

import os
import shutil
import sys
import warnings
from typing import IO, TYPE_CHECKING, Any, Callable

from sphinx.deprecation import RemovedInSphinx90Warning

if TYPE_CHECKING:
    import builtins

warnings.warn("'sphinx.testing.path' is deprecated. "
              "Use 'os.path' or 'pathlib' instead.",
              RemovedInSphinx90Warning, stacklevel=2)

FILESYSTEMENCODING = sys.getfilesystemencoding() or sys.getdefaultencoding()


def getumask() -> int:
    """Get current umask value"""
    umask = os.umask(0)  # Note: Change umask value temporarily to obtain it
    os.umask(umask)

    return umask


UMASK = getumask()


class path(str):
    """
    Represents a path which behaves like a string.
    """

    __slots__ = ()

    @property
    def parent(self) -> path:
        """
        The name of the directory the file or directory is in.
        """
        return self.__class__(os.path.dirname(self))

    def basename(self) -> str:
        return os.path.basename(self)

    def abspath(self) -> path:
        """
        Returns the absolute path.
        """
        return self.__class__(os.path.abspath(self))

    def isabs(self) -> bool:
        """
        Returns ``True`` if the path is absolute.
        """
        return os.path.isabs(self)

    def isdir(self) -> bool:
        """
        Returns ``True`` if the path is a directory.
        """
        return os.path.isdir(self)

    def isfile(self) -> bool:
        """
        Returns ``True`` if the path is a file.
        """
        return os.path.isfile(self)

    def islink(self) -> bool:
        """
        Returns ``True`` if the path is a symbolic link.
        """
        return os.path.islink(self)

    def ismount(self) -> bool:
        """
        Returns ``True`` if the path is a mount point.
        """
        return os.path.ismount(self)

    def rmtree(self, ignore_errors: bool = False, onerror: Callable | None = None) -> None:
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

    def copytree(self, destination: str, symlinks: bool = False) -> None:
        """
        Recursively copy a directory to the given `destination`. If the given
        `destination` does not exist it will be created.

        :param symlinks:
            If ``True`` symbolic links in the source tree result in symbolic
            links in the destination tree otherwise the contents of the files
            pointed to by the symbolic links are copied.
        """
        shutil.copytree(self, destination, symlinks=symlinks)
        if os.environ.get('SPHINX_READONLY_TESTDIR'):
            # If source tree is marked read-only (e.g. because it is on a read-only
            # filesystem), `shutil.copytree` will mark the destination as read-only
            # as well.  To avoid failures when adding additional files/directories
            # to the destination tree, ensure destination directories are not marked
            # read-only.
            for root, _dirs, files in os.walk(destination):
                os.chmod(root, 0o755 & ~UMASK)
                for name in files:
                    os.chmod(os.path.join(root, name), 0o644 & ~UMASK)

    def movetree(self, destination: str) -> None:
        """
        Recursively move the file or directory to the given `destination`
        similar to the  Unix "mv" command.

        If the `destination` is a file it may be overwritten depending on the
        :func:`os.rename` semantics.
        """
        shutil.move(self, destination)

    move = movetree

    def unlink(self) -> None:
        """
        Removes a file.
        """
        os.unlink(self)

    def stat(self) -> Any:
        """
        Returns a stat of the file.
        """
        return os.stat(self)

    def utime(self, arg: Any) -> None:
        os.utime(self, arg)

    def open(self, mode: str = 'r', **kwargs: Any) -> IO:
        return open(self, mode, **kwargs)

    def write_text(self, text: str, encoding: str = 'utf-8', **kwargs: Any) -> None:
        """
        Writes the given `text` to the file.
        """
        with open(self, 'w', encoding=encoding, **kwargs) as f:
            f.write(text)

    def read_text(self, encoding: str = 'utf-8', **kwargs: Any) -> str:
        """
        Returns the text in the file.
        """
        with open(self, encoding=encoding, **kwargs) as f:
            return f.read()

    def read_bytes(self) -> builtins.bytes:
        """
        Returns the bytes in the file.
        """
        with open(self, mode='rb') as f:
            return f.read()

    def write_bytes(self, bytes: str, append: bool = False) -> None:
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

    def exists(self) -> bool:
        """
        Returns ``True`` if the path exist.
        """
        return os.path.exists(self)

    def lexists(self) -> bool:
        """
        Returns ``True`` if the path exists unless it is a broken symbolic
        link.
        """
        return os.path.lexists(self)

    def makedirs(self, mode: int = 0o777, exist_ok: bool = False) -> None:
        """
        Recursively create directories.
        """
        os.makedirs(self, mode, exist_ok=exist_ok)

    def joinpath(self, *args: Any) -> path:
        """
        Joins the path with the argument given and returns the result.
        """
        return self.__class__(os.path.join(self, *map(self.__class__, args)))

    def listdir(self) -> list[str]:
        return os.listdir(self)

    __div__ = __truediv__ = joinpath

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({super().__repr__()})'
