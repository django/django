import errno
import os
from datetime import datetime

from django.conf import settings
from django.contrib.staticfiles.storage import CachedStaticFilesStorage
from django.core.files import storage


class DummyStorage(storage.Storage):
    """
    A storage class that does implement modified_time() but raises
    NotImplementedError when calling
    """
    def _save(self, name, content):
        return 'dummy'

    def delete(self, name):
        pass

    def exists(self, name):
        pass

    def modified_time(self, name):
        return datetime.date(1970, 1, 1)


class PathNotImplementedStorage(storage.Storage):

    def _save(self, name, content):
        return 'dummy'

    def _path(self, name):
        return os.path.join(settings.STATIC_ROOT, name)

    def exists(self, name):
        return os.path.exists(self._path(name))

    def listdir(self, path):
        path = self._path(path)
        directories, files = [], []
        for entry in os.listdir(path):
            if os.path.isdir(os.path.join(path, entry)):
                directories.append(entry)
            else:
                files.append(entry)
        return directories, files

    def delete(self, name):
        name = self._path(name)
        if os.path.exists(name):
            try:
                os.remove(name)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

    def path(self, name):
        raise NotImplementedError


class SimpleCachedStaticFilesStorage(CachedStaticFilesStorage):

    def file_hash(self, name, content=None):
        return 'deploy12345'
