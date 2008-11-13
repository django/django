import os
from os.path import join, normcase, normpath, abspath, isabs, sep
from django.utils.encoding import force_unicode

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
    # We need to use normcase to ensure we don't false-negative on case
    # insensitive operating systems (like Windows).
    base = force_unicode(base)
    paths = [force_unicode(p) for p in paths]
    final_path = normcase(abspathu(join(base, *paths)))
    base_path = normcase(abspathu(base))
    base_path_len = len(base_path)
    # Ensure final_path starts with base_path and that the next character after
    # the final path is os.sep (or nothing, in which case final_path must be
    # equal to base_path).
    if not final_path.startswith(base_path) \
       or final_path[base_path_len:base_path_len+1] not in ('', sep):
        raise ValueError('the joined path is located outside of the base path'
                         ' component')
    return final_path
