from os.path import join, normcase, abspath, sep

def safe_join(base, *paths):
    """
    Joins one or more path components to the base path component intelligently.
    Returns a normalized, absolute version of the final path.

    The final path must be located inside of the base path component (otherwise
    a ValueError is raised).
    """
    # We need to use normcase to ensure we don't false-negative on case
    # insensitive operating systems (like Windows).
    final_path = normcase(abspath(join(base, *paths)))
    base_path = normcase(abspath(base))
    base_path_len = len(base_path)
    # Ensure final_path starts with base_path and that the next character after
    # the final path is os.sep (or nothing, in which case final_path must be
    # equal to base_path).
    if not final_path.startswith(base_path) \
       or final_path[base_path_len:base_path_len+1] not in ('', sep):
        raise ValueError('the joined path is located outside of the base path'
                         ' component')
    return final_path
