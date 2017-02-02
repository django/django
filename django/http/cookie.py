import sys
from http import cookies

# Cookie pickling bug is fixed in Python 3.4.3+
# http://bugs.python.org/issue22775
if sys.version_info >= (3, 4, 3):
    SimpleCookie = cookies.SimpleCookie
else:
    Morsel = cookies.Morsel

    class SimpleCookie(cookies.SimpleCookie):
        def __setitem__(self, key, value):
            if isinstance(value, Morsel):
                # allow assignment of constructed Morsels (e.g. for pickling)
                dict.__setitem__(self, key, value)
            else:
                super().__setitem__(key, value)


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
