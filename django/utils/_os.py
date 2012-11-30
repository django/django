import os
import stat
import sys
from os.path import join, normcase, normpath, abspath, isabs, sep, dirname
from django.utils import six

try:
    WindowsError = WindowsError
except NameError:
    class WindowsError(Exception):
        pass


if six.PY3:
    fs_encoding = sys.getfilesystemencoding()

    def path_as_str(path):
        """Convert a filesystem path from bytes to str, if necessary."""
        return path if isinstance(path, str) else path.decode(fs_encoding)

    def path_as_text(path):
        """No-op -- paths are unicode by default on Python 3."""
        return path
else:
    # In Python < 3.2, sys.getfilesystemencoding() may return None under Unix.
    fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()

    def path_as_str(path):
        """Convert a filesystem path from unicode to str, if necessary."""
        return path if isinstance(path, str) else path.encode(fs_encoding)

    def path_as_text(path):
        """Convert a filesystem path from str to unicode, if necessary."""
        return path if isinstance(path, six.text_type) else path.decode(fs_encoding)


def safe_join(base, *paths):
    """
    Joins one or more path components to the base path component intelligently.
    Returns a normalized, absolute version of the final path.

    The final path must be located inside of the base path component (otherwise
    a ValueError is raised).
    """
    final_path = os.path.abspath(join(base, *paths))
    base_path = os.path.abspath(base)
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
        raise ValueError('The joined path (%s) is located outside of the base '
                         'path component (%s)' % (final_path, base_path))
    return final_path


def rmtree_errorhandler(func, path, exc_info):
    """
    On Windows, some files are read-only (e.g. in in .svn dirs), so when
    rmtree() tries to remove them, an exception is thrown.
    We catch that here, remove the read-only attribute, and hopefully
    continue without problems.
    """
    exctype, value = exc_info[:2]
    # looking for a windows error
    if exctype is not WindowsError or 'Access is denied' not in str(value):
        raise
    # file type should currently be read only
    if ((os.stat(path).st_mode & stat.S_IREAD) != stat.S_IREAD):
        raise
    # convert to read/write
    os.chmod(path, stat.S_IWRITE)
    # use the original function to repeat the operation
    func(path)

