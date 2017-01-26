import os
import tempfile
from os.path import abspath, dirname, join, normcase, sep

from django.core.exceptions import SuspiciousFileOperation
from django.utils.encoding import force_text

# For backwards-compatibility in Django 2.0
abspathu = abspath


def upath(path):
    """Always return a unicode path (did something for Python 2)."""
    return path


def npath(path):
    """
    Always return a native path, that is unicode on Python 3 and bytestring on
    Python 2. Noop for Python 3.
    """
    return path


def safe_join(base, *paths):
    """
    Joins one or more path components to the base path component intelligently.
    Returns a normalized, absolute version of the final path.

    The final path must be located inside of the base path component (otherwise
    a ValueError is raised).
    """
    base = force_text(base)
    paths = [force_text(p) for p in paths]
    final_path = abspath(join(base, *paths))
    base_path = abspath(base)
    # Ensure final_path starts with base_path (using normcase to ensure we
    # don't false-negative on case insensitive operating systems like Windows),
    # further, one of the following conditions must be true:
    #  a) The next character is the path separator (to prevent conditions like
    #     safe_join("/dir", "/../d"))
    #  b) The final path must be the same as the base path.
    #  c) The base path must be the most root path (meaning either "/" or "C:\\")
    if (not normcase(final_path).startswith(normcase(base_path + sep)) and
            normcase(final_path) != normcase(base_path) and
            dirname(normcase(base_path)) != normcase(base_path)):
        raise SuspiciousFileOperation(
            'The joined path ({}) is located outside of the base path '
            'component ({})'.format(final_path, base_path))
    return final_path


def symlinks_supported():
    """
    A function to check if creating symlinks are supported in the
    host platform and/or if they are allowed to be created (e.g.
    on Windows it requires admin permissions).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        original_path = os.path.join(temp_dir, 'original')
        symlink_path = os.path.join(temp_dir, 'symlink')
        os.makedirs(original_path)
        try:
            os.symlink(original_path, symlink_path)
            supported = True
        except (OSError, NotImplementedError):
            supported = False
        return supported
