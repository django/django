"""
The temp module provides a NamedTemporaryFile that can be re-opened on any
platform. Most platforms use the standard Python tempfile.TemporaryFile class,
but MS Windows users are given a custom class.

This is needed because in Windows NT, the default implementation of
NamedTemporaryFile uses the O_TEMPORARY flag, and thus cannot be reopened [1].

1: http://mail.python.org/pipermail/python-list/2005-December/359474.html
"""

import os
import tempfile
from django.core.files.utils import FileProxyMixin

__all__ = ('NamedTemporaryFile', 'gettempdir',)

if os.name == 'nt':
    class TemporaryFile(FileProxyMixin):
        """
        Temporary file object constructor that works in Windows and supports
        reopening of the temporary file in windows.
        """
        def __init__(self, mode='w+b', bufsize=-1, suffix='', prefix='',
                dir=None):
            fd, name = tempfile.mkstemp(suffix=suffix, prefix=prefix,
                                          dir=dir)
            self.name = name
            self.file = os.fdopen(fd, mode, bufsize)
            self.close_called = False

        # Because close can be called during shutdown
        # we need to cache os.unlink and access it
        # as self.unlink only
        unlink = os.unlink

        def close(self):
            if not self.close_called:
                self.close_called = True
                try:
                    self.file.close()
                except (OSError, IOError):
                    pass
                try:
                    self.unlink(self.name)
                except (OSError):
                    pass

        def __del__(self):
            self.close()

    NamedTemporaryFile = TemporaryFile
else:
    NamedTemporaryFile = tempfile.NamedTemporaryFile

gettempdir = tempfile.gettempdir
