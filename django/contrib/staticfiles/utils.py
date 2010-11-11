import fnmatch
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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

def check_settings():
    """
    Checks if the MEDIA_(ROOT|URL) and STATICFILES_(ROOT|URL)
    settings have the same value.
    """
    if settings.MEDIA_URL == settings.STATICFILES_URL:
        raise ImproperlyConfigured("The MEDIA_URL and STATICFILES_URL "
                                   "settings must have individual values")
    if ((settings.MEDIA_ROOT and settings.STATICFILES_ROOT) and
            (settings.MEDIA_ROOT == settings.STATICFILES_ROOT)):
        raise ImproperlyConfigured("The MEDIA_ROOT and STATICFILES_ROOT "
                                   "settings must have individual values")
