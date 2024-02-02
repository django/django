from django.core.files.storage.filesystem import FileSystemStorage


class NoReadException(Exception):
    pass


class NoReadStorageMixin:
    def open(self, *args, **kwargs):
        raise NoReadException("This storage class does not support reading.")


class NoReadFileSystemStorage(NoReadStorageMixin, FileSystemStorage):
    """A storage backend which does not support reading.

    Use this to test the behavior of Django when a storage backend is not
    supposed to do any additional reads."""
