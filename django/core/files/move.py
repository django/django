"""
Move a file in the safest way possible::

    >>> from django.core.files.move import file_move_save
    >>> file_move_save("/tmp/old_file", "/tmp/new_file")
"""

import os
from django.core.files import locks

__all__ = ['file_move_safe']

try:
    import shutil
    file_move = shutil.move
except ImportError:
    file_move = os.rename

def file_move_safe(old_file_name, new_file_name, chunk_size = 1024*64, allow_overwrite=False):
    """
    Moves a file from one location to another in the safest way possible.

    First, try using ``shutils.move``, which is OS-dependent but doesn't break
    if moving across filesystems. Then, try ``os.rename``, which will break
    across filesystems. Finally, streams manually from one file to another in
    pure Python.

    If the destination file exists and ``allow_overwrite`` is ``False``, this
    function will throw an ``IOError``.
    """

    # There's no reason to move if we don't have to.
    if old_file_name == new_file_name:
        return

    if not allow_overwrite and os.path.exists(new_file_name):
        raise IOError("Cannot overwrite existing file '%s'." % new_file_name)

    try:
        file_move(old_file_name, new_file_name)
        return
    except OSError:
        # This will happen with os.rename if moving to another filesystem
        pass

    # If the built-in didn't work, do it the hard way.
    fd = os.open(new_file_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0))
    try:
        locks.lock(fd, locks.LOCK_EX)
        old_file = open(old_file_name, 'rb')
        current_chunk = None
        while current_chunk != '':
            current_chunk = old_file.read(chunk_size)
            os.write(fd, current_chunk)
    finally:
        locks.unlock(fd)
        os.close(fd)
        old_file.close()

    os.remove(old_file_name)
