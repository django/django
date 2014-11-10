import os
import sys

from django.apps import apps
from django.utils import lru_cache
from django.utils import six


@lru_cache.lru_cache()
def get_app_template_dirs(dirname):
    """
    Return an iterable of paths of directories to load app templates from.

    dirname is the name of the subdirectory containing templates inside
    installed applications.
    """
    if six.PY2:
        fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
    template_dirs = []
    for app_config in apps.get_app_configs():
        if not app_config.path:
            continue
        template_dir = os.path.join(app_config.path, dirname)
        if os.path.isdir(template_dir):
            if six.PY2:
                template_dir = template_dir.decode(fs_encoding)
            template_dirs.append(template_dir)
    # Immutable return value because it will be cached and shared by callers.
    return tuple(template_dirs)
