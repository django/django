from operator import attrgetter


class FileProxyMixin:
    """
    A mixin class used to forward file methods to an underlaying file
    object.  The internal file object has to be called "file"::

        class FileProxy(FileProxyMixin):
            def __init__(self, file):
                self.file = file
    """

    encoding = property(attrgetter('file.encoding'))
    fileno = property(attrgetter('file.fileno'))
    flush = property(attrgetter('file.flush'))
    isatty = property(attrgetter('file.isatty'))
    newlines = property(attrgetter('file.newlines'))
    read = property(attrgetter('file.read'))
    readinto = property(attrgetter('file.readinto'))
    readline = property(attrgetter('file.readline'))
    readlines = property(attrgetter('file.readlines'))
    seek = property(attrgetter('file.seek'))
    tell = property(attrgetter('file.tell'))
    truncate = property(attrgetter('file.truncate'))
    write = property(attrgetter('file.write'))
    writelines = property(attrgetter('file.writelines'))

    @property
    def closed(self):
        return not self.file or self.file.closed

    def readable(self):
        if self.closed:
            return False
        if hasattr(self.file, 'readable'):
            return self.file.readable()
        return True

    def writable(self):
        if self.closed:
            return False
        if hasattr(self.file, 'writable'):
            return self.file.writable()
        return 'w' in getattr(self.file, 'mode', '')

    def seekable(self):
        if self.closed:
            return False
        if hasattr(self.file, 'seekable'):
            return self.file.seekable()
        return True

    def __iter__(self):
        return iter(self.file)
