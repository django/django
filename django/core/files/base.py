import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.utils.encoding import smart_str, smart_unicode
from django.core.files.utils import FileProxyMixin

class File(FileProxyMixin):
    DEFAULT_CHUNK_SIZE = 64 * 2**10

    def __init__(self, file, name=None):
        self.file = file
        if name is None:
            name = getattr(file, 'name', None)
        self.name = name
        self.mode = getattr(file, 'mode', None)
        self.closed = False

    def __str__(self):
        return smart_str(self.name or '')

    def __unicode__(self):
        return smart_unicode(self.name or u'')

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self or "None")

    def __nonzero__(self):
        return bool(self.name)

    def __len__(self):
        return self.size

    def _get_size(self):
        if not hasattr(self, '_size'):
            if hasattr(self.file, 'size'):
                self._size = self.file.size
            elif os.path.exists(self.file.name):
                self._size = os.path.getsize(self.file.name)
            else:
                raise AttributeError("Unable to determine the file's size.")
        return self._size

    def _set_size(self, size):
        self._size = size

    size = property(_get_size, _set_size)

    def chunks(self, chunk_size=None):
        """
        Read the file and yield chucks of ``chunk_size`` bytes (defaults to
        ``UploadedFile.DEFAULT_CHUNK_SIZE``).
        """
        if not chunk_size:
            chunk_size = self.DEFAULT_CHUNK_SIZE

        if hasattr(self, 'seek'):
            self.seek(0)
        # Assume the pointer is at zero...
        counter = self.size

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
            chunk_size = self.DEFAULT_CHUNK_SIZE
        return self.size > chunk_size

    def __iter__(self):
        # Iterate over this file-like object by newlines
        buffer_ = None
        for chunk in self.chunks():
            chunk_buffer = StringIO(chunk)

            for line in chunk_buffer:
                if buffer_:
                    line = buffer_ + line
                    buffer_ = None

                # If this is the end of a line, yield
                # otherwise, wait for the next round
                if line[-1] in ('\n', '\r'):
                    yield line
                else:
                    buffer_ = line

        if buffer_ is not None:
            yield buffer_

    def open(self, mode=None):
        if not self.closed:
            self.seek(0)
        elif os.path.exists(self.file.name):
            self.file = open(self.file.name, mode or self.file.mode)
            self.closed = False
        else:
            raise ValueError("The file cannot be reopened.")

    def close(self):
        self.file.close()
        self.closed = True

class ContentFile(File):
    """
    A File-like object that takes just raw content, rather than an actual file.
    """
    def __init__(self, content):
        content = content or ''
        super(ContentFile, self).__init__(StringIO(content))
        self.size = len(content)

    def __str__(self):
        return 'Raw content'

    def __nonzero__(self):
        return True

    def open(self, mode=None):
        if self.closed:
            self.closed = False
        self.seek(0)
