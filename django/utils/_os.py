import os
import tempfile
from os.path import abspath, dirname, join, normcase, sep
from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation


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
    if not isinstance(value, Path):
        value = Path(value)
    return value
