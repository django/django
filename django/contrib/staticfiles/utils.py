import fnmatch
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def matches_patterns(path, patterns=None):
    """
    Return True or False depending on whether the ``path`` should be
    ignored (if it matches any pattern in ``ignore_patterns``).
    """
    if patterns is None:
        patterns = []
    for pattern in patterns:
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def get_files(storage, ignore_patterns=None, location=''):
    """
    Recursively walk the storage directories yielding the paths
    of all files that should be copied.
    """
    if ignore_patterns is None:
        ignore_patterns = []
    directories, files = storage.listdir(location)
    for fn in files:
        if matches_patterns(fn, ignore_patterns):
            continue
        if location:
            fn = os.path.join(location, fn)
        yield fn
    for dir in directories:
        if matches_patterns(dir, ignore_patterns):
            continue
        if location:
            dir = os.path.join(location, dir)
        for fn in get_files(storage, ignore_patterns, dir):
            yield fn


def check_settings(base_url=None):
    """
    Checks if the staticfiles settings have sane values.
    """
    if 'static' not in settings.FILE_STORAGES:
        raise ImproperlyConfigured("File storage for static files is not configured.")

    if 'media' not in settings.FILE_STORAGES:
        raise ImproperlyConfigured("File storage for media files is not configured.")

    static_storage_settings = settings.FILE_STORAGES['static']
    media_storage_settings = settings.FILE_STORAGES['media']

    if base_url is None:
        base_url = static_storage_settings.get('url', None)

    if not base_url:
        raise ImproperlyConfigured(
            "You're using the staticfiles app "
            "without having set the url setting in the options for static files "
            "storage backend.")

    if media_storage_settings.get('url', None) == base_url:
        raise ImproperlyConfigured("URL settings for static and media file storages "
                                   "must have different values")

    media_storage_location = media_storage_settings.get('location', None)
    static_storage_location = static_storage_settings.get('location', None)
    if ((media_storage_location and static_storage_location) and
            (media_storage_location == static_storage_location)):
        raise ImproperlyConfigured("Location settings for static and media files storages "
                                   "must have different values")
