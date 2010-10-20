import os
from django.conf import settings
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage, Storage, FileSystemStorage
from django.utils.datastructures import SortedDict
from django.utils.functional import memoize, LazyObject
from django.utils.importlib import import_module

from django.contrib.staticfiles import utils
from django.contrib.staticfiles.storage import AppStaticStorage

_finders = {}


class BaseFinder(object):
    """
    A base file finder to be used for custom staticfiles finder classes.

    """
    def find(self, path, all=False):
        """
        Given a relative file path this ought to find an
        absolute file path.

        If the ``all`` parameter is ``False`` (default) only
        the first found file path will be returned; if set
        to ``True`` a list of all found files paths is returned.
        """
        raise NotImplementedError()

    def list(self, ignore_patterns=[]):
        """
        Given an optional list of paths to ignore, this should return
        a three item iterable with path, prefix and a storage instance.
        """
        raise NotImplementedError()


class FileSystemFinder(BaseFinder):
    """
    A static files finder that uses the ``STATICFILES_DIRS`` setting
    to locate files.
    """
    storages = SortedDict()
    locations = set()

    def __init__(self, apps=None, *args, **kwargs):
        for root in settings.STATICFILES_DIRS:
            if isinstance(root, (list, tuple)):
                prefix, root = root
            else:
                prefix = ''
            self.locations.add((prefix, root))
        # Don't initialize multiple storages for the same location
        for prefix, root in self.locations:
            self.storages[root] = FileSystemStorage(location=root)
        super(FileSystemFinder, self).__init__(*args, **kwargs)

    def find(self, path, all=False):
        """
        Looks for files in the extra media locations
        as defined in ``STATICFILES_DIRS``.
        """
        matches = []
        for prefix, root in self.locations:
            matched_path = self.find_location(root, path, prefix)
            if matched_path:
                if not all:
                    return matched_path
                matches.append(matched_path)
        return matches

    def find_location(self, root, path, prefix=None):
        """
        Find a requested static file in a location, returning the found
        absolute path (or ``None`` if no match).
        """
        if prefix:
            prefix = '%s/' % prefix
            if not path.startswith(prefix):
                return None
            path = path[len(prefix):]
        path = os.path.join(root, path)
        if os.path.exists(path):
            return path

    def list(self, ignore_patterns):
        """
        List all files in all locations.
        """
        for prefix, root in self.locations:
            storage = self.storages[root]
            for path in utils.get_files(storage, ignore_patterns):
                yield path, prefix, storage


class AppDirectoriesFinder(BaseFinder):
    """
    A static files finder that looks in the ``media`` directory of each app.
    """
    storages = {}
    storage_class = AppStaticStorage

    def __init__(self, apps=None, *args, **kwargs):
        if apps is not None:
            self.apps = apps
        else:
            self.apps = models.get_apps()
        for app in self.apps:
            self.storages[app] = self.storage_class(app)
        super(AppDirectoriesFinder, self).__init__(*args, **kwargs)

    def list(self, ignore_patterns):
        """
        List all files in all app storages.
        """
        for storage in self.storages.itervalues():
            if storage.exists(''): # check if storage location exists
                prefix = storage.get_prefix()
                for path in utils.get_files(storage, ignore_patterns):
                    yield path, prefix, storage

    def find(self, path, all=False):
        """
        Looks for files in the app directories.
        """
        matches = []
        for app in self.apps:
            app_matches = self.find_in_app(app, path)
            if app_matches:
                if not all:
                    return app_matches
                matches.append(app_matches)
        return matches

    def find_in_app(self, app, path):
        """
        Find a requested static file in an app's media locations.
        """
        storage = self.storages[app]
        prefix = storage.get_prefix()
        if prefix:
            prefix = '%s/' % prefix
            if not path.startswith(prefix):
                return None
            path = path[len(prefix):]
        # only try to find a file if the source dir actually exists
        if storage.exists(path):
            matched_path = storage.path(path)
            if matched_path:
                return matched_path


class BaseStorageFinder(BaseFinder):
    """
    A base static files finder to be used to extended
    with an own storage class.
    """
    storage = None

    def __init__(self, storage=None, *args, **kwargs):
        if storage is not None:
            self.storage = storage
        if self.storage is None:
            raise ImproperlyConfigured("The staticfiles storage finder %r "
                                       "doesn't have a storage class "
                                       "assigned." % self.__class__)
        # Make sure we have an storage instance here.
        if not isinstance(self.storage, (Storage, LazyObject)):
            self.storage = self.storage()
        super(BaseStorageFinder, self).__init__(*args, **kwargs)

    def find(self, path, all=False):
        """
        Looks for files in the default file storage, if it's local.
        """
        try:
            self.storage.path('')
        except NotImplementedError:
            pass
        else:
            if self.storage.exists(path):
                match = self.storage.path(path)
                if all:
                    match = [match]
                return match
        return []

    def list(self, ignore_patterns):
        """
        List all files of the storage.
        """
        for path in utils.get_files(self.storage, ignore_patterns):
            yield path, '', self.storage

class DefaultStorageFinder(BaseStorageFinder):
    """
    A static files finder that uses the default storage backend.
    """
    storage = default_storage


def find(path, all=False):
    """
    Find a requested static file, first looking in any defined extra media
    locations and next in any (non-excluded) installed apps.
    
    If no matches are found and the static location is local, look for a match
    there too.
    
    If ``all`` is ``False`` (default), return the first matching
    absolute path (or ``None`` if no match). Otherwise return a list of
    found absolute paths.
    
    """
    matches = []
    for finder in get_finders():
        result = finder.find(path, all=all)
        if not all and result:
            return result
        if not isinstance(result, (list, tuple)):
            result = [result]
        matches.extend(result)
    if matches:
        return matches
    # No match.
    return all and [] or None

def get_finders():
    for finder_path in settings.STATICFILES_FINDERS:
        yield get_finder(finder_path)

def _get_finder(import_path):
    """
    Imports the message storage class described by import_path, where
    import_path is the full Python path to the class.
    """
    module, attr = import_path.rsplit('.', 1)
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                   (module, e))
    try:
        Finder = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '
                                   'class.' % (module, attr))
    if not issubclass(Finder, BaseFinder):
        raise ImproperlyConfigured('Finder "%s" is not a subclass of "%s"' %
                                   (Finder, BaseFinder))
    return Finder()
get_finder = memoize(_get_finder, _finders, 1)
