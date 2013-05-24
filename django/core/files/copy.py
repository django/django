"""
Copy a file in the safest way possible::

    >>> from django.core.files.copy import file_copy_safe
    >>> file_copy_safe("/tmp/old_file", "/tmp/new_file")
"""

import os
from shutil import copystat

from django.core.files import locks


__all__ = ['file_copy_safe']


def file_copy_safe(old_file_name, new_file_name, chunk_size=1024*64, allow_overwrite=False):
    """
    Copy a file from one location to another in the safest way possible.

    If the destination file exists and ``allow_overwrite`` is ``False``, this
    function will throw an ``IOError``.
    """
    # first open the old file, so that it won't go away
    with open(old_file_name, 'rb') as old_file:
        # now open the new file, not forgetting allow_overwrite
        fd = os.open(new_file_name, os.O_WRONLY | os.O_CREAT | getattr(os, 'O_BINARY', 0) |
                                    (not allow_overwrite and os.O_EXCL or 0))
        try:
            locks.lock(fd, locks.LOCK_EX)
            current_chunk = None
            while current_chunk != b'':
                current_chunk = old_file.read(chunk_size)
                os.write(fd, current_chunk)
        except OSError:
            os.remove(new_file_name)
            raise
        finally:
            locks.unlock(fd)
            os.close(fd)
    copystat(old_file_name, new_file_name)
