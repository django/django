import errno
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.staticfiles.storage import CachedStaticFilesStorage
from django.core.files import storage
from django.utils import timezone


class DummyStorage(storage.Storage):
    """
    A storage class that implements get_modified_time() but raises
    NotImplementedError for path().
    """
    def _save(self, name, content):
        return 'dummy'

    def delete(self, name):
        pass

    def exists(self, name):
        pass

    def get_modified_time(self, name):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


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
        try:
            os.remove(name)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def path(self, name):
        raise NotImplementedError


class NeverCopyRemoteStorage(PathNotImplementedStorage):
    """
    Return a future modified time for all files so that nothing is collected.
    """
    def get_modified_time(self, name):
        return datetime.now() + timedelta(days=30)


class QueryStringStorage(storage.Storage):
    def url(self, path):
        return path + '?a=b&c=d'


class SimpleCachedStaticFilesStorage(CachedStaticFilesStorage):

    def file_hash(self, name, content=None):
        return 'deploy12345'


class ExtraPatternsCachedStaticFilesStorage(CachedStaticFilesStorage):
    """
    A storage class to test pattern substitutions with more than one pattern
    entry. The added pattern rewrites strings like "url(...)" to JS_URL("...").
    """
    patterns = tuple(CachedStaticFilesStorage.patterns) + (
        (
            "*.js", (
                (r"""(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""", 'JS_URL("%s")'),
            ),
        ),
    )
