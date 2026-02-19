import os
import pathlib

from django.core.exceptions import SuspiciousFileOperation


def validate_file_name(name, allow_relative_path=False):
    # Remove potentially dangerous names
    if os.path.basename(name) in {"", ".", ".."}:
        raise SuspiciousFileOperation("Could not derive file name from '%s'" % name)

    if allow_relative_path:
        # Ensure that name can be treated as a pure posix path, i.e. Unix
        # style (with forward slashes).
        path = pathlib.PurePosixPath(str(name).replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise SuspiciousFileOperation(
                "Detected path traversal attempt in '%s'" % name
            )
    elif name != os.path.basename(name):
        raise SuspiciousFileOperation("File name '%s' includes path elements" % name)

    return name


class FileProxyMixin:
    """
    A mixin class used to forward file methods to an underlying file
    object. The internal file object has to be called "file"::

        class FileProxy(FileProxyMixin):
            def __init__(self, file):
                self.file = file
    """

    def __getattr__(self, name):
        return getattr(self.file, name)


    @property
    def closed(self):
        return not self.file or self.file.closed

    def readable(self):
        if self.closed:
            return False
        if hasattr(self.file, "readable"):
            return self.file.readable()
        return True

    def writable(self):
        if self.closed:
            return False
        if hasattr(self.file, "writable"):
            return self.file.writable()
        return "w" in getattr(self.file, "mode", "")

    def seekable(self):
        if self.closed:
            return False
        if hasattr(self.file, "seekable"):
            return self.file.seekable()
        return True

    def __iter__(self):
        return iter(self.file)
