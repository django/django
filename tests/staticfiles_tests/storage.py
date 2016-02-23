from datetime import datetime

from django.contrib.staticfiles.storage import CachedStaticFilesStorage
from django.core.files import storage
from django.utils import timezone


class DummyStorage(storage.Storage):
    """
    A storage class that implements get_modified_time().
    """
    def _save(self, name, content):
        return 'dummy'

    def delete(self, name):
        pass

    def exists(self, name):
        pass

    def get_modified_time(self, name):
        return datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)


class SimpleCachedStaticFilesStorage(CachedStaticFilesStorage):

    def file_hash(self, name, content=None):
        return 'deploy12345'
