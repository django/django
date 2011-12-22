import os
import stat
from os.path import join, normcase, normpath, abspath, isabs, sep
from django.utils.encoding import force_unicode

try:
    WindowsError = WindowsError
except NameError:
    class WindowsError(Exception):
        pass


# Define our own abspath function that can handle joining
# unicode paths to a current working directory that has non-ASCII
# characters in it.  This isn't necessary on Windows since the
# Windows version of abspath handles this correctly.  The Windows
# abspath also handles drive letters differently than the pure
# Python implementation, so it's best not to replace it.
if os.name == 'nt':
    abspathu = abspath
else:
    def abspathu(path):
        """
        Version of os.path.abspath that uses the unicode representation
        of the current working directory, thus avoiding a UnicodeDecodeError
        in join when the cwd has non-ASCII characters.
        """
        if not isabs(path):
            path = join(os.getcwdu(), path)
        return normpath(path)

def safe_join(base, *paths):
    """
    Joins one or more path components to the base path component intelligently.
    Returns a normalized, absolute version of the final path.

    The final path must be located inside of the base path component (otherwise
    a ValueError is raised).
    """
    base = force_unicode(base)
    paths = [force_unicode(p) for p in paths]
    final_path = abspathu(join(base, *paths))
    base_path = abspathu(base)
    base_path_len = len(base_path)
    # Ensure final_path starts with base_path (using normcase to ensure we
    # don't false-negative on case insensitive operating systems like Windows)
    # and that the next character after the final path is os.sep (or nothing,
    # in which case final_path must be equal to base_path).
    if not normcase(final_path).startswith(normcase(base_path)) \
       or final_path[base_path_len:base_path_len+1] not in ('', sep):
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
    # lookin for a windows error
    if exctype is not WindowsError or 'Access is denied' not in str(value):
        raise
    # file type should currently be read only
    if ((os.stat(path).st_mode & stat.S_IREAD) != stat.S_IREAD):
        raise
    # convert to read/write
    os.chmod(path, stat.S_IWRITE)
    # use the original function to repeat the operation
    func(path)

