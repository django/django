import os
from django.conf import settings
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage, Storage, FileSystemStorage
from django.utils.datastructures import SortedDict
from django.utils.functional import memoize, LazyObject
from django.utils.importlib import import_module
from django.utils._os import safe_join

from django.contrib.staticfiles import utils
from django.contrib.staticfiles.storage import AppStaticStorage

_finders = SortedDict()


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
    def __init__(self, apps=None, *args, **kwargs):
        # Maps dir paths to an appropriate storage instance
        self.storages = SortedDict()
        # Set of locations with static files
        self.locations = set()
        for root in settings.STATICFILES_DIRS:
            if isinstance(root, (list, tuple)):
                prefix, root = root
            else:
                prefix = ''
            self.locations.add((prefix, root))
        # Don't initialize multiple storages for the same location
        for prefix, root in self.locations:
            filesystem_storage = FileSystemStorage(location=root)
            filesystem_storage.prefix = prefix
            self.storages[root] = filesystem_storage

        super(FileSystemFinder, self).__init__(*args, **kwargs)

    def find(self, path, all=False):
        """
        Looks for files in the extra locations
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
        Finds a requested static file in a location, returning the found
        absolute path (or ``None`` if no match).
        """
        if prefix:
            prefix = '%s%s' % (prefix, os.sep)
            if not path.startswith(prefix):
                return None
            path = path[len(prefix):]
        path = safe_join(root, path)
        if os.path.exists(path):
            return path

    def list(self, ignore_patterns):
        """
        List all files in all locations.
        """
        for prefix, root in self.locations:
            storage = self.storages[root]
            for path in utils.get_files(storage, ignore_patterns):
                yield path, storage


class AppDirectoriesFinder(BaseFinder):
    """
    A static files finder that looks in the directory of each app as
    specified in the source_dir attribute of the given storage class.
    """
    storage_class = AppStaticStorage

    def __init__(self, apps=None, *args, **kwargs):
        # The list of apps that are handled
        self.apps = []
        # Mapping of app module paths to storage instances
        self.storages = SortedDict()
        if apps is None:
            apps = settings.INSTALLED_APPS
        for app in apps:
            app_storage = self.storage_class(app)
            if os.path.isdir(app_storage.location):
                self.storages[app] = app_storage
                if app not in self.apps:
                    self.apps.append(app)
        super(AppDirectoriesFinder, self).__init__(*args, **kwargs)

    def list(self, ignore_patterns):
        """
        List all files in all app storages.
        """
        for storage in self.storages.itervalues():
            if storage.exists(''): # check if storage location exists
                for path in utils.get_files(storage, ignore_patterns):
                    yield path, storage

    def find(self, path, all=False):
        """
        Looks for files in the app directories.
        """
        matches = []
        for app in self.apps:
            match = self.find_in_app(app, path)
            if match:
                if not all:
                    return match
                matches.append(match)
        return matches

    def find_in_app(self, app, path):
        """
        Find a requested static file in an app's static locations.
        """
        storage = self.storages.get(app, None)
        if storage:
            if storage.prefix:
                prefix = '%s%s' % (storage.prefix, os.sep)
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
            yield path, self.storage

class DefaultStorageFinder(BaseStorageFinder):
    """
    A static files finder that uses the default storage backend.
    """
    storage = default_storage


def find(path, all=False):
    """
    Find a static file with the given path using all enabled finders.

    If ``all`` is ``False`` (default), return the first matching
    absolute path (or ``None`` if no match). Otherwise return a list.
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
    Imports the staticfiles finder class described by import_path, where
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
