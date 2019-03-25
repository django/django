# $Id: _compat.py 7486 2012-07-11 12:25:14Z milde $
# Author: Georg Brandl <georg@python.org>
# Copyright: This module has been placed in the public domain.

"""
Python 2/3 compatibility definitions.

This module currently provides the following helper symbols:

* bytes (name of byte string type; str in 2.x, bytes in 3.x)
* b (function converting a string literal to an ASCII byte string;
  can be also used to convert a Unicode string into a byte string)
* u_prefix (unicode repr prefix: 'u' in 2.x, '' in 3.x)
  (Required in docutils/test/test_publisher.py)
* BytesIO (a StringIO class that works with bytestrings)
"""

import sys

if sys.version_info < (3,0):
    b = bytes = str
    u_prefix = 'u'
    from io import StringIO as BytesIO
else:
    import builtins
    bytes = builtins.bytes
    u_prefix = ''
    def b(s):
        if isinstance(s, str):
            return s.encode('latin1')
        elif isinstance(s, bytes):
            return s
        else:
            raise TypeError("Invalid argument %r for b()" % (s,))
    # using this hack since 2to3 "fixes" the relative import
    # when using ``from io import BytesIO``
    BytesIO = __import__('io').BytesIO

if sys.version_info < (2,5):
    import builtins

    def __import__(name, globals={}, locals={}, fromlist=[], level=-1):
        """Compatibility definition for Python 2.4.

        Silently ignore the `level` argument missing in Python < 2.5.
        """
        # we need the level arg because the default changed in Python 3.3
        return builtins.__import__(name, globals, locals, fromlist)
