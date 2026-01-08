from __future__ import annotations

import os
import sys
from contextlib import suppress
from errno import EACCES
from pathlib import Path
from typing import cast

from ._api import BaseFileLock
from ._util import ensure_directory_exists, raise_on_not_writable_file

if sys.platform == "win32":  # pragma: win32 cover
    import ctypes
    import msvcrt
    from ctypes import wintypes

    # Windows API constants for reparse point detection
    FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

    # Load kernel32.dll
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    _kernel32.GetFileAttributesW.restype = wintypes.DWORD

    def _is_reparse_point(path: str) -> bool:
        """
        Check if a path is a reparse point (symlink, junction, etc.) on Windows.

        :param path: Path to check
        :return: True if path is a reparse point, False otherwise
        :raises OSError: If GetFileAttributesW fails for reasons other than file-not-found
        """
        attrs = _kernel32.GetFileAttributesW(path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            # File doesn't exist yet - that's fine, we'll create it
            err = ctypes.get_last_error()
            if err == 2:  # noqa: PLR2004  # ERROR_FILE_NOT_FOUND
                return False
            if err == 3:  # noqa: PLR2004 # ERROR_PATH_NOT_FOUND
                return False
            # Some other error - let caller handle it
            return False
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)

    class WindowsFileLock(BaseFileLock):
        """Uses the :func:`msvcrt.locking` function to hard lock the lock file on Windows systems."""

        def _acquire(self) -> None:
            raise_on_not_writable_file(self.lock_file)
            ensure_directory_exists(self.lock_file)

            # Security check: Refuse to open reparse points (symlinks, junctions)
            # This prevents TOCTOU symlink attacks (CVE-TBD)
            if _is_reparse_point(self.lock_file):
                msg = f"Lock file is a reparse point (symlink/junction): {self.lock_file}"
                raise OSError(msg)

            flags = (
                os.O_RDWR  # open for read and write
                | os.O_CREAT  # create file if not exists
                | os.O_TRUNC  # truncate file if not empty
            )
            try:
                fd = os.open(self.lock_file, flags, self._context.mode)
            except OSError as exception:
                if exception.errno != EACCES:  # has no access to this lock
                    raise
            else:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                except OSError as exception:
                    os.close(fd)  # close file first
                    if exception.errno != EACCES:  # file is already locked
                        raise
                else:
                    self._context.lock_file_fd = fd

        def _release(self) -> None:
            fd = cast("int", self._context.lock_file_fd)
            self._context.lock_file_fd = None
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            os.close(fd)

            with suppress(OSError):  # Probably another instance of the application hat acquired the file lock.
                Path(self.lock_file).unlink()

else:  # pragma: win32 no cover

    class WindowsFileLock(BaseFileLock):
        """Uses the :func:`msvcrt.locking` function to hard lock the lock file on Windows systems."""

        def _acquire(self) -> None:
            raise NotImplementedError

        def _release(self) -> None:
            raise NotImplementedError


__all__ = [
    "WindowsFileLock",
]
