import fnmatch

def get_files(storage, ignore_patterns=[], location=''):
    """
    Recursively walk the storage directories gathering a complete list of files
    that should be copied, returning this list.
    
    """
    def is_ignored(path):
        """
        Return True or False depending on whether the ``path`` should be
        ignored (if it matches any pattern in ``ignore_patterns``).
        
        """
        for pattern in ignore_patterns:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        return False

    directories, files = storage.listdir(location)
    static_files = [location and '/'.join([location, fn]) or fn
                    for fn in files
                    if not is_ignored(fn)]
    for dir in directories:
        if is_ignored(dir):
            continue
        if location:
            dir = '/'.join([location, dir])
        static_files.extend(get_files(storage, ignore_patterns, dir))
    return static_files
