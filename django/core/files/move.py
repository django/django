"""
Move a file in the safest way possible::

    >>> from django.core.files.move import file_move_safe
    >>> file_move_safe("/tmp/old_file", "/tmp/new_file")
"""

import os
from shutil import copymode, copystat

from django.core.files import locks

__all__ = ["file_move_safe"]


def file_move_safe(
    old_file_name, new_file_name, chunk_size=1024 * 64, allow_overwrite=False
):
    """
    Move a file from one location to another in the safest way possible.

    First, try ``os.rename``, which is simple but will break across
    filesystems. If that fails, stream manually from one file to another in
    pure Python.

    If the destination file exists and ``allow_overwrite`` is ``False``, raise
    ``FileExistsError``.
    """
    # There's no reason to move if we don't have to.
    try:
        if os.path.samefile(old_file_name, new_file_name):
            return
    except OSError:
        pass

    if not allow_overwrite and os.access(new_file_name, os.F_OK):
        raise FileExistsError(
            f"Destination file {new_file_name} exists and allow_overwrite is False."
        )

    try:
        os.rename(old_file_name, new_file_name)
        return
    except OSError:
        # OSError happens with os.rename() if moving to another filesystem or
        # when moving opened files on certain operating systems.
        pass

    # first open the old file, so that it won't go away
    with open(old_file_name, "rb") as old_file:
        # now open the new file, not forgetting allow_overwrite
        fd = os.open(
            new_file_name,
            (
                os.O_WRONLY
                | os.O_CREAT
                | getattr(os, "O_BINARY", 0)
                | (os.O_EXCL if not allow_overwrite else 0)
                | os.O_TRUNC
            ),
        )
        try:
            locks.lock(fd, locks.LOCK_EX)
            current_chunk = None
            while current_chunk != b"":
                current_chunk = old_file.read(chunk_size)
                os.write(fd, current_chunk)
        finally:
            locks.unlock(fd)
            os.close(fd)

    try:
        copystat(old_file_name, new_file_name)
    except PermissionError:
        # Certain filesystems (e.g. CIFS) fail to copy the file's metadata if
        # the type of the destination filesystem isn't the same as the source
        # filesystem. This also happens with some SELinux-enabled systems.
        # Ignore that, but try to set basic permissions.
        try:
            copymode(old_file_name, new_file_name)
        except PermissionError:
            pass

    try:
        os.remove(old_file_name)
    except PermissionError as e:
        # Certain operating systems (Cygwin and Windows)
        # fail when deleting opened files, ignore it. (For the
        # systems where this happens, temporary files will be auto-deleted
        # on close anyway.)
        if getattr(e, "winerror", 0) != 32:
            raise
