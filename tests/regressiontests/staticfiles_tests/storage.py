from datetime import datetime
from django.core.files import storage
from django.contrib.staticfiles.storage import CachedStaticFilesStorage

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


class SimpleCachedStaticFilesStorage(CachedStaticFilesStorage):

    def file_hash(self, name, content=None):
        return 'deploy12345'
