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

__all__ = ('NamedTemporaryFile', 'gettempdir',)

if os.name == 'nt':
    class TemporaryFile(object):
        """
        Temporary file object constructor that works in Windows and supports
        reopening of the temporary file in windows.
        """
        def __init__(self, mode='w+b', bufsize=-1, suffix='', prefix='',
                dir=None):
            fd, name = tempfile.mkstemp(suffix=suffix, prefix=prefix,
                                          dir=dir)
            self.name = name
            self._file = os.fdopen(fd, mode, bufsize)

        def __del__(self):
            try:
                self._file.close()
            except (OSError, IOError):
                pass
            try:
                os.unlink(self.name)
            except (OSError):
                pass

            try:
                super(TemporaryFile, self).__del__()
            except AttributeError:
                pass


        def read(self, *args):          return self._file.read(*args)
        def seek(self, offset):         return self._file.seek(offset)
        def write(self, s):             return self._file.write(s)
        def close(self):                return self._file.close()
        def __iter__(self):             return iter(self._file)
        def readlines(self, size=None): return self._file.readlines(size)
        def xreadlines(self):           return self._file.xreadlines()

    NamedTemporaryFile = TemporaryFile
else:
    NamedTemporaryFile = tempfile.NamedTemporaryFile

gettempdir = tempfile.gettempdir
