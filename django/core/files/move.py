"""
Move a file in the safest way possible::

    >>> from django.core.files.move import file_move_safe
    >>> file_move_safe("/tmp/old_file", "/tmp/new_file")
"""

import os
from shutil import copystat

from django.core.files import locks

__all__ = ['file_move_safe']


def _samefile(src, dst):
    # Macintosh, Unix.
    if hasattr(os.path, 'samefile'):
        try:
            return os.path.samefile(src, dst)
        except OSError:
            return False

    # All other platforms: check for same pathname.
    return (os.path.normcase(os.path.abspath(src)) ==
            os.path.normcase(os.path.abspath(dst)))


def file_move_safe(old_file_name, new_file_name, chunk_size=1024 * 64, allow_overwrite=False):
    """
    Moves a file from one location to another in the safest way possible.

    First, tries ``os.rename``, which is simple but will break across filesystems.
    If that fails, streams manually from one file to another in pure Python.

    If the destination file exists and ``allow_overwrite`` is ``False``, this
    function will throw an ``IOError``.
    """

    # There's no reason to move if we don't have to.
    if _samefile(old_file_name, new_file_name):
        return

    try:
        # If the destination file exists and allow_overwrite is False then raise an IOError
        if not allow_overwrite and os.access(new_file_name, os.F_OK):
            raise IOError("Destination file %s exists and allow_overwrite is False" % new_file_name)

        os.rename(old_file_name, new_file_name)
        return
    except OSError:
        # This will happen with os.rename if moving to another filesystem
        # or when moving opened files on certain operating systems
        pass

    # first open the old file, so that it won't go away
    with open(old_file_name, 'rb') as old_file:
        # now open the new file, not forgetting allow_overwrite
        fd = os.open(new_file_name, (os.O_WRONLY | os.O_CREAT | getattr(os, 'O_BINARY', 0) |
                                     (os.O_EXCL if not allow_overwrite else 0)))
        try:
            locks.lock(fd, locks.LOCK_EX)
            current_chunk = None
            while current_chunk != b'':
                current_chunk = old_file.read(chunk_size)
                os.write(fd, current_chunk)
        finally:
            locks.unlock(fd)
            os.close(fd)
    copystat(old_file_name, new_file_name)

    try:
        os.remove(old_file_name)
    except OSError as e:
        # Certain operating systems (Cygwin and Windows)
        # fail when deleting opened files, ignore it.  (For the
        # systems where this happens, temporary files will be auto-deleted
        # on close anyway.)
        if getattr(e, 'winerror', 0) != 32 and getattr(e, 'errno', 0) != 13:
            raise
