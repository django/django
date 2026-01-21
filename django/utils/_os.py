import os
import tempfile
from os.path import abspath, curdir, dirname, join, normcase, sep
from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation


# Copied verbatim (minus `os.path` fixes) from:
# https://github.com/python/cpython/pull/23901.
# Python versions >= PY315 may include this fix, so periodic checks are needed
# to remove this vendored copy of `makedirs` once solved upstream.
def makedirs(name, mode=0o777, exist_ok=False, *, parent_mode=None):
    """makedirs(name [, mode=0o777][, exist_ok=False][, parent_mode=None])

    Super-mkdir; create a leaf directory and all intermediate ones.  Works like
    mkdir, except that any intermediate path segment (not just the rightmost)
    will be created if it does not exist. If the target directory already
    exists, raise an OSError if exist_ok is False. Otherwise no exception is
    raised.  If parent_mode is not None, it will be used as the mode for any
    newly-created, intermediate-level directories. Otherwise, intermediate
    directories are created with the default permissions (respecting umask).
    This is recursive.

    """
    head, tail = os.path.split(name)
    if not tail:
        head, tail = os.path.split(head)
    if head and tail and not os.path.exists(head):
        try:
            if parent_mode is not None:
                makedirs(
                    head, mode=parent_mode, exist_ok=exist_ok, parent_mode=parent_mode
                )
            else:
                makedirs(head, exist_ok=exist_ok)
        except FileExistsError:
            # Defeats race condition when another thread created the path
            pass
        cdir = curdir
        if isinstance(tail, bytes):
            cdir = bytes(curdir, "ASCII")
        if tail == cdir:  # xxx/newdir/. exists if xxx/newdir exists
            return
    try:
        os.mkdir(name, mode)
        # PY315: The call to `chmod()` is not in the CPython proposed code.
        # Apply `chmod()` after `mkdir()` to enforce the exact requested
        # permissions, since the kernel masks the mode argument with the
        # process umask. This guarantees consistent directory permissions
        # without mutating global umask state.
        os.chmod(name, mode)
    except OSError:
        # Cannot rely on checking for EEXIST, since the operating system
        # could give priority to other errors like EACCES or EROFS
        if not exist_ok or not os.path.isdir(name):
            raise


def safe_makedirs(name, mode=0o777, exist_ok=False):
    """Create directories recursively with explicit `mode` on each level."""
    makedirs(name=name, mode=mode, exist_ok=exist_ok, parent_mode=mode)


def safe_join(base, *paths):
    """
    Join one or more path components to the base path component intelligently.
    Return a normalized, absolute version of the final path.

    Raise SuspiciousFileOperation if the final path isn't located inside of the
    base path component.
    """
    final_path = abspath(join(base, *paths))
    base_path = abspath(base)
    # Ensure final_path starts with base_path (using normcase to ensure we
    # don't false-negative on case insensitive operating systems like Windows),
    # further, one of the following conditions must be true:
    #  a) The next character is the path separator (to prevent conditions like
    #     safe_join("/dir", "/../d"))
    #  b) The final path must be the same as the base path.
    #  c) The base path must be the most root path (meaning either "/" or "C:\\")
    if (
        not normcase(final_path).startswith(normcase(base_path + sep))
        and normcase(final_path) != normcase(base_path)
        and dirname(normcase(base_path)) != normcase(base_path)
    ):
        raise SuspiciousFileOperation(
            "The joined path ({}) is located outside of the base path "
            "component ({})".format(final_path, base_path)
        )
    return final_path


def symlinks_supported():
    """
    Return whether or not creating symlinks are supported in the host platform
    and/or if they are allowed to be created (e.g. on Windows it requires admin
    permissions).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        original_path = os.path.join(temp_dir, "original")
        symlink_path = os.path.join(temp_dir, "symlink")
        os.makedirs(original_path)
        try:
            os.symlink(original_path, symlink_path)
            supported = True
        except (OSError, NotImplementedError):
            supported = False
        return supported


def to_path(value):
    """Convert value to a pathlib.Path instance, if not already a Path."""
    if isinstance(value, Path):
        return value
    elif not isinstance(value, str):
        raise TypeError("Invalid path type: %s" % type(value).__name__)
    return Path(value)
