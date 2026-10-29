import functools
import os

import django


@functools.cache
def django_file_prefixes():
    file = getattr(django, "__file__", None)
    if file is None:
        return ()
    return (os.path.join(os.path.dirname(file), ""),)
