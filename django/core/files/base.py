import os
from io import BytesIO, StringIO, UnsupportedOperation

from django.core.files.utils import FileProxyMixin
from django.utils.functional import cached_property


class File(FileProxyMixin):
    DEFAULT_CHUNK_SIZE = 64 * 2 ** 10

    def __init__(self, file, name=None):
        self.file = file
        if name is None:
            name = getattr(file, 'name', None)
        self.name = name
        if hasattr(file, 'mode'):
            self.mode = file.mode

    def __str__(self):
        return self.name or ''

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self or "None")

    def __bool__(self):
        return bool(self.name)

    def __len__(self):
        return self.size

    @cached_property
    def size(self):
        if hasattr(self.file, 'size'):
            return self.file.size
        if hasattr(self.file, 'name'):
            try:
                return os.path.getsize(self.file.name)
            except (OSError, TypeError):
                pass
        if hasattr(self.file, 'tell') and hasattr(self.file, 'seek'):
            pos = self.file.tell()
            self.file.seek(0, os.SEEK_END)
            size = self.file.tell()
            self.file.seek(pos)
            return size
        raise AttributeError("Unable to determine the file's size.")

    def chunks(self, chunk_size=None):
        """
        Read the file and yield chunks of ``chunk_size`` bytes (defaults to
        ``File.DEFAULT_CHUNK_SIZE``).
        """
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
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
        Return ``True`` if you can expect multiple chunks.

        NB: If a particular file representation is in memory, subclasses should
        always return ``False`` -- there's no good reason to read from memory in
        chunks.
        """
        return self.size > (chunk_size or self.DEFAULT_CHUNK_SIZE)

    def __iter__(self):
        # Iterate over this file-like object by newlines
        buffer_ = None
        for chunk in self.chunks():
            for line in chunk.splitlines(True):
                if buffer_:
                    if endswith_cr(buffer_) and not equals_lf(line):
                        # Line split after a \r newline; yield buffer_.
                        yield buffer_
                        # Continue with line.
                    else:
                        # Line either split without a newline (line
                        # continues after buffer_) or with \r\n
                        # newline (line == b'\n').
                        line = buffer_ + line
                    # buffer_ handled, clear it.
                    buffer_ = None

                # If this is the end of a \n or \r\n line, yield.
                if endswith_lf(line):
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
        return self

    def close(self):
        self.file.close()


class ContentFile(File):
    """
    A File-like object that takes just raw content, rather than an actual file.
    """
    def __init__(self, content, name=None):
        stream_class = StringIO if isinstance(content, str) else BytesIO
        super().__init__(stream_class(content), name=name)
        self.size = len(content)

    def __str__(self):
        return 'Raw content'

    def __bool__(self):
        return True

    def open(self, mode=None):
        self.seek(0)
        return self

    def close(self):
        pass

    def write(self, data):
        self.__dict__.pop('size', None)  # Clear the computed size.
        return self.file.write(data)


def endswith_cr(line):
    """Return True if line (a text or bytestring) ends with '\r'."""
    return line.endswith('\r' if isinstance(line, str) else b'\r')


def endswith_lf(line):
    """Return True if line (a text or bytestring) ends with '\n'."""
    return line.endswith('\n' if isinstance(line, str) else b'\n')


def equals_lf(line):
    """Return True if line (a text or bytestring) equals '\n'."""
    return line == ('\n' if isinstance(line, str) else b'\n')
