import sys

from django.utils.six.moves import http_cookies

# Cookie pickling bug is fixed in Python 2.7.9 and Python 3.4.3+
# http://bugs.python.org/issue22775
cookie_pickles_properly = (
    (sys.version_info[:2] == (2, 7) and sys.version_info >= (2, 7, 9)) or
    sys.version_info >= (3, 4, 3)
)

if cookie_pickles_properly:
    SimpleCookie = http_cookies.SimpleCookie
else:
    Morsel = http_cookies.Morsel

    class SimpleCookie(http_cookies.SimpleCookie):
        if not cookie_pickles_properly:
            def __setitem__(self, key, value):
                # Apply the fix from http://bugs.python.org/issue22775 where
                # it's not fixed in Python itself
                if isinstance(value, Morsel):
                    # allow assignment of constructed Morsels (e.g. for pickling)
                    dict.__setitem__(self, key, value)
                else:
                    super(SimpleCookie, self).__setitem__(key, value)


def parse_cookie(cookie):
    """
    Return a dictionary parsed from a `Cookie:` header string.
    """
    cookiedict = {}
    for chunk in cookie.split(str(';')):
        if str('=') in chunk:
            key, val = chunk.split(str('='), 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = str(''), chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookiedict[key] = http_cookies._unquote(val)
    return cookiedict
