"""
Classes representing uploaded files.
"""

import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__all__ = ('UploadedFile', 'TemporaryUploadedFile', 'InMemoryUploadedFile')

class UploadedFile(object):
    """
    A abstract uploadded file (``TemporaryUploadedFile`` and
    ``InMemoryUploadedFile`` are the built-in concrete subclasses).

    An ``UploadedFile`` object behaves somewhat like a file object and
    represents some file data that the user submitted with a form.
    """
    DEFAULT_CHUNK_SIZE = 64 * 2**10

    def __init__(self, file_name=None, content_type=None, file_size=None, charset=None):
        self.file_name = file_name
        self.file_size = file_size
        self.content_type = content_type
        self.charset = charset

    def __repr__(self):
        return "<%s: %s (%s)>" % (self.__class__.__name__, self.file_name, self.content_type)

    def _set_file_name(self, name):
        # Sanitize the file name so that it can't be dangerous.
        if name is not None:
            # Just use the basename of the file -- anything else is dangerous.
            name = os.path.basename(name)
            
            # File names longer than 255 characters can cause problems on older OSes.
            if len(name) > 255:
                name, ext = os.path.splitext(name)
                name = name[:255 - len(ext)] + ext
                
        self._file_name = name
        
    def _get_file_name(self):
        return self._file_name
        
    file_name = property(_get_file_name, _set_file_name)

    def chunk(self, chunk_size=None):
        """
        Read the file and yield chucks of ``chunk_size`` bytes (defaults to
        ``UploadedFile.DEFAULT_CHUNK_SIZE``).
        """
        if not chunk_size:
            chunk_size = UploadedFile.DEFAULT_CHUNK_SIZE

        if hasattr(self, 'seek'):
            self.seek(0)
        # Assume the pointer is at zero...
        counter = self.file_size

        while counter > 0:
            yield self.read(chunk_size)
            counter -= chunk_size

    def multiple_chunks(self, chunk_size=None):
        """
        Returns ``True`` if you can expect multiple chunks.

        NB: If a particular file representation is in memory, subclasses should
        always return ``False`` -- there's no good reason to read from memory in
        chunks.
        """
        if not chunk_size:
            chunk_size = UploadedFile.DEFAULT_CHUNK_SIZE
        return self.file_size < chunk_size

    # Abstract methods; subclasses *must* default read() and probably should
    # define open/close.
    def read(self, num_bytes=None):
        raise NotImplementedError()

    def open(self):
        pass

    def close(self):
        pass

    # Backwards-compatible support for uploaded-files-as-dictionaries.
    def __getitem__(self, key):
        import warnings
        warnings.warn(
            message = "The dictionary access of uploaded file objects is deprecated. Use the new object interface instead.",
            category = DeprecationWarning,
            stacklevel = 2
        )
        backwards_translate = {
            'filename': 'file_name',
            'content-type': 'content_type',
            }

        if key == 'content':
            return self.read()
        elif key == 'filename':
            return self.file_name
        elif key == 'content-type':
            return self.content_type
        else:
            return getattr(self, key)

class TemporaryUploadedFile(UploadedFile):
    """
    A file uploaded to a temporary location (i.e. stream-to-disk).
    """

    def __init__(self, file, file_name, content_type, file_size, charset):
        super(TemporaryUploadedFile, self).__init__(file_name, content_type, file_size, charset)
        self.file = file
        self.path = file.name
        self.file.seek(0)

    def temporary_file_path(self):
        """
        Returns the full path of this file.
        """
        return self.path

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

    def open(self):
        self.seek(0)

    def seek(self, *args, **kwargs):
        self.file.seek(*args, **kwargs)

class InMemoryUploadedFile(UploadedFile):
    """
    A file uploaded into memory (i.e. stream-to-memory).
    """
    def __init__(self, file, field_name, file_name, content_type, file_size, charset):
        super(InMemoryUploadedFile, self).__init__(file_name, content_type, file_size, charset)
        self.file = file
        self.field_name = field_name
        self.file.seek(0)

    def seek(self, *args, **kwargs):
        self.file.seek(*args, **kwargs)

    def open(self):
        self.seek(0)

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

    def chunk(self, chunk_size=None):
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
        self.file_name = name
        self.field_name = None
        self.file_size = len(content or '')
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
