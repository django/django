import fnmatch
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import get_prefixed_static_url, get_prefixed_media_url


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


def check_settings():
    """
    Checks if the staticfiles settings have sane values.
    """
    if not settings.STATIC_URL:
        raise ImproperlyConfigured(
            "You're using the staticfiles app "
            "without having set the required STATIC_URL setting.")
    if settings.MEDIA_URL == settings.STATIC_URL:
        raise ImproperlyConfigured("The MEDIA_URL and STATIC_URL "
                                   "settings must have different values")
    if ((settings.MEDIA_ROOT and settings.STATIC_ROOT) and
            (settings.MEDIA_ROOT == settings.STATIC_ROOT)):
        raise ImproperlyConfigured("The MEDIA_ROOT and STATIC_ROOT "
                                   "settings must have different values")


def check_base_url(base_url=None):
    """
    Checks if the base static URL differs from media URL.
    """
    if base_url is None:
        base_url = get_prefixed_static_url()
    if get_prefixed_media_url() == base_url:
        raise ImproperlyConfigured("The media and static URLs must have different values")
