"""
Classes representing uploaded files.
"""

import os
import warnings
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.files.base import File

from django.core.files import temp as tempfile

__all__ = ('UploadedFile', 'TemporaryUploadedFile', 'InMemoryUploadedFile', 'SimpleUploadedFile')

# Because we fooled around with it a bunch, UploadedFile has a bunch
# of deprecated properties. This little shortcut helps define 'em
# without too much code duplication.
def deprecated_property(old, new, readonly=False):
    def issue_warning():
        warnings.warn(
            message = "UploadedFile.%s is deprecated; use UploadedFile.%s instead." % (old, new),
            category = DeprecationWarning,
            stacklevel = 3
        )
    
    def getter(self):
        issue_warning()
        return getattr(self, new)
        
    def setter(self, value):
        issue_warning()
        setattr(self, new, value)
        
    if readonly:
        return property(getter)
    else:
        return property(getter, setter)

class UploadedFile(File):
    """
    A abstract uploaded file (``TemporaryUploadedFile`` and
    ``InMemoryUploadedFile`` are the built-in concrete subclasses).

    An ``UploadedFile`` object behaves somewhat like a file object and
    represents some file data that the user submitted with a form.
    """
    DEFAULT_CHUNK_SIZE = 64 * 2**10

    def __init__(self, name=None, content_type=None, size=None, charset=None):
        self.name = name
        self.size = size
        self.content_type = content_type
        self.charset = charset

    def __repr__(self):
        return "<%s: %s (%s)>" % (self.__class__.__name__, self.name, self.content_type)

    def _get_name(self):
        return self._name

    def _set_name(self, name):
        # Sanitize the file name so that it can't be dangerous.
        if name is not None:
            # Just use the basename of the file -- anything else is dangerous.
            name = os.path.basename(name)

            # File names longer than 255 characters can cause problems on older OSes.
            if len(name) > 255:
                name, ext = os.path.splitext(name)
                name = name[:255 - len(ext)] + ext

        self._name = name

    name = property(_get_name, _set_name)

    # Deprecated properties
    filename = deprecated_property(old="filename", new="name")
    file_name = deprecated_property(old="file_name", new="name")
    file_size = deprecated_property(old="file_size", new="size")
    chunk = deprecated_property(old="chunk", new="chunks", readonly=True)

    def _get_data(self):
        warnings.warn(
            message = "UploadedFile.data is deprecated; use UploadedFile.read() instead.",
            category = DeprecationWarning,
            stacklevel = 2
        )
        return self.read()
    data = property(_get_data)

    # Abstract methods; subclasses *must* define read() and probably should
    # define open/close.
    def read(self, num_bytes=None):
        raise NotImplementedError()

    def open(self):
        pass

    def close(self):
        pass

    # Backwards-compatible support for uploaded-files-as-dictionaries.
    def __getitem__(self, key):
        warnings.warn(
            message = "The dictionary access of uploaded file objects is deprecated. Use the new object interface instead.",
            category = DeprecationWarning,
            stacklevel = 2
        )
        backwards_translate = {
            'filename': 'name',
            'content-type': 'content_type',
        }

        if key == 'content':
            return self.read()
        elif key == 'filename':
            return self.name
        elif key == 'content-type':
            return self.content_type
        else:
            return getattr(self, key)

class TemporaryUploadedFile(UploadedFile):
    """
    A file uploaded to a temporary location (i.e. stream-to-disk).
    """
    def __init__(self, name, content_type, size, charset):
        super(TemporaryUploadedFile, self).__init__(name, content_type, size, charset)
        if settings.FILE_UPLOAD_TEMP_DIR:
            self._file = tempfile.NamedTemporaryFile(suffix='.upload', dir=settings.FILE_UPLOAD_TEMP_DIR)
        else:
            self._file = tempfile.NamedTemporaryFile(suffix='.upload')

    def temporary_file_path(self):
        """
        Returns the full path of this file.
        """
        return self._file.name
    
    # Most methods on this object get proxied to NamedTemporaryFile.
    # We can't directly subclass because NamedTemporaryFile is actually a
    # factory function
    def read(self, *args):          return self._file.read(*args)
    def seek(self, offset):         return self._file.seek(offset)
    def write(self, s):             return self._file.write(s)
    def __iter__(self):             return iter(self._file)
    def readlines(self, size=None): return self._file.readlines(size)
    def xreadlines(self):           return self._file.xreadlines()
    def close(self):
        try:
            return self._file.close()
        except OSError, e:
            if e.errno == 2:
                # Means the file was moved or deleted before the tempfile could unlink it.
                # Still sets self._file.close_called and calls self._file.file.close()
                # before the exception
                return
            else: 
                raise e
        
class InMemoryUploadedFile(UploadedFile):
    """
    A file uploaded into memory (i.e. stream-to-memory).
    """
    def __init__(self, file, field_name, name, content_type, size, charset):
        super(InMemoryUploadedFile, self).__init__(name, content_type, size, charset)
        self.file = file
        self.field_name = field_name
        self.file.seek(0)

    def seek(self, *args, **kwargs):
        self.file.seek(*args, **kwargs)

    def open(self):
        self.seek(0)

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

    def chunks(self, chunk_size=None):
        self.file.seek(0)
        yield self.read()

    def multiple_chunks(self, chunk_size=None):
        # Since it's in memory, we'll never have multiple chunks.
        return False

class SimpleUploadedFile(InMemoryUploadedFile):
    """
    A simple representation of a file, which just has content, size, and a name.
    """
    def __init__(self, name, content, content_type='text/plain'):
        self.file = StringIO(content or '')
        self.name = name
        self.field_name = None
        self.size = len(content or '')
        self.content_type = content_type
        self.charset = None
        self.file.seek(0)

    def from_dict(cls, file_dict):
        """
        Creates a SimpleUploadedFile object from
        a dictionary object with the following keys:
           - filename
           - content-type
           - content
        """
        return cls(file_dict['filename'],
                   file_dict['content'],
                   file_dict.get('content-type', 'text/plain'))

    from_dict = classmethod(from_dict)
