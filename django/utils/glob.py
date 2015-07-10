from __future__ import unicode_literals

import os.path
import re

from django.utils import six

# backport of Python 3.4's glob.escape

if six.PY3:
    from glob import escape as glob_escape
else:
    _magic_check = re.compile('([*?[])')

    def glob_escape(pathname):
        """
        Escape all special characters.
        """
        drive, pathname = os.path.splitdrive(pathname)
        pathname = _magic_check.sub(r'[\1]', pathname)
        return drive + pathname
