from __future__ import unicode_literals

import os.path
import re

from django.utils import six

# backport of Python 3.4's glob.escape

try:
    from glob import escape as glob_escape
except ImportError:
    _magic_check = re.compile('([*?[])')

    if six.PY3:
        _magic_check_bytes = re.compile(b'([*?[])')

        def glob_escape(pathname):
            """
            Escape all special characters.
            """
            drive, pathname = os.path.splitdrive(pathname)
            if isinstance(pathname, bytes):
                pathname = _magic_check_bytes.sub(br'[\1]', pathname)
            else:
                pathname = _magic_check.sub(r'[\1]', pathname)
            return drive + pathname

    else:
        def glob_escape(pathname):
            """
            Escape all special characters.
            """
            drive, pathname = os.path.splitdrive(pathname)
            pathname = _magic_check.sub(r'[\1]', pathname)
            return drive + pathname
