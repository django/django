import sys
from http import cookies

if sys.version_info < (3, 7, 0):
    # Monkey patch the Morsel and SimpleCookie objects
    # to support SameSite attribute
    # added in 3.7 https://github.com/python/cpython/pull/214
    class Morsel(cookies.Morsel):
        def __init__(self):
            self._reserved['samesite'] = 'SameSite'
            super().__init__()

    cookies.Morsel = Morsel

    if sys.version_info < (3, 4, 3):

        class SimpleCookie(cookies.SimpleCookie):

            # Cookie pickling bug is fixed in Python 3.4.3+
            # http://bugs.python.org/issue22775

                def __setitem__(self, key, value):
                    if isinstance(value, Morsel):
                        # allow assignment of constructed Morsels (e.g. for pickling)
                        dict.__setitem__(self, key, value)
                    else:
                        super().__setitem__(key, value)

        cookies.SimpleCookie = SimpleCookie
else:
    # Python 3.7+
    SimpleCookie = cookies.SimpleCookie

def parse_cookie(cookie):
    """
    Return a dictionary parsed from a `Cookie:` header string.
    """
    cookiedict = {}
    for chunk in cookie.split(';'):
        if '=' in chunk:
            key, val = chunk.split('=', 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = '', chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookiedict[key] = cookies._unquote(val)
    return cookiedict
