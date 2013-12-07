import imp

def module_fs_path(app_name):
    """
    Determines the path to the module for the given app_name,
    without actually importing the application.

    Raises ImportError if it cannot be found for any reason.
    """
    parts = app_name.split('.')
    parts.reverse()
    path = None

    while parts:
        part = parts.pop()
        f, path, descr = imp.find_module(part, [path] if path else None)
        if f:
            f.close()
    return path
