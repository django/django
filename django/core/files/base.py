from __future__ import unicode_literals

import os
from io import BytesIO, StringIO, UnsupportedOperation

from django.utils.encoding import smart_text
from django.core.files.utils import FileProxyMixin
from django.utils import six
from django.utils.encoding import force_bytes, python_2_unicode_compatible

@python_2_unicode_compatible
class File(FileProxyMixin):
    DEFAULT_CHUNK_SIZE = 64 * 2**10

    def __init__(self, file, name=None):
        self.file = file
        if name is None:
            name = getattr(file, 'name', None)
        self.name = name
        if hasattr(file, 'mode'):
            self.mode = file.mode

    def __str__(self):
        return smart_text(self.name or '')

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self or "None")

    def __bool__(self):
        return bool(self.name)

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __len__(self):
        return self.size

    def _get_size(self):
        if not hasattr(self, '_size'):
            if hasattr(self.file, 'size'):
                self._size = self.file.size
            elif hasattr(self.file, 'name') and os.path.exists(self.file.name):
                self._size = os.path.getsize(self.file.name)
            elif hasattr(self.file, 'tell') and hasattr(self.file, 'seek'):
                pos = self.file.tell()
                self.file.seek(0, os.SEEK_END)
                self._size = self.file.tell()
                self.file.seek(pos)
            else:
                raise AttributeError("Unable to determine the file's size.")
        return self._size

    def _set_size(self, size):
        self._size = size

    size = property(_get_size, _set_size)

    def _get_closed(self):
        return not self.file or self.file.closed
    closed = property(_get_closed)

    def chunks(self, chunk_size=None):
        """
        Read the file and yield chucks of ``chunk_size`` bytes (defaults to
        ``UploadedFile.DEFAULT_CHUNK_SIZE``).
        """
        if not chunk_size:
            chunk_size = self.DEFAULT_CHUNK_SIZE

        try:
            self.seek(0)
        except (AttributeError, UnsupportedOperation):
            pass

        while True:
            data = self.read(chunk_size)
            if not data:
                break
            yield data

    def multiple_chunks(self, chunk_size=None):
        """
        Returns ``True`` if you can expect multiple chunks.

        NB: If a particular file representation is in memory, subclasses should
        always return ``False`` -- there's no good reason to read from memory in
        chunks.
        """
        if not chunk_size:
            chunk_size = self.DEFAULT_CHUNK_SIZE
        return self.size > chunk_size

    def __iter__(self):
        # Iterate over this file-like object by newlines
        buffer_ = None
        for chunk in self.chunks():
            chunk_buffer = BytesIO(chunk)

            for line in chunk_buffer:
                if buffer_:
                    line = buffer_ + line
                    buffer_ = None

                # If this is the end of a line, yield
                # otherwise, wait for the next round
                if line[-1:] in (b'\n', b'\r'):
                    yield line
                else:
                    buffer_ = line

        if buffer_ is not None:
            yield buffer_

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def open(self, mode=None):
        if not self.closed:
            self.seek(0)
        elif self.name and os.path.exists(self.name):
            self.file = open(self.name, mode or self.mode)
        else:
            raise ValueError("The file cannot be reopened.")

    def close(self):
        self.file.close()

@python_2_unicode_compatible
class ContentFile(File):
    """
    A File-like object that takes just raw content, rather than an actual file.
    """
    def __init__(self, content, name=None):
        if six.PY3:
            stream_class = StringIO if isinstance(content, six.text_type) else BytesIO
        else:
            stream_class = BytesIO
            content = force_bytes(content)
        super(ContentFile, self).__init__(stream_class(content), name=name)
        self.size = len(content)

    def __str__(self):
        return 'Raw content'

    def __bool__(self):
        return True

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def open(self, mode=None):
        self.seek(0)

    def close(self):
        pass
