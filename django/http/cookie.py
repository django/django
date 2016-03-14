from __future__ import unicode_literals

import sys

from django.utils import six
from django.utils.encoding import force_str
from django.utils.six.moves import http_cookies

# http://bugs.python.org/issue2193 is fixed in Python 3.3+.
_cookie_allows_colon_in_names = six.PY3

# Cookie pickling bug is fixed in Python 2.7.9 and Python 3.4.3+
# http://bugs.python.org/issue22775
cookie_pickles_properly = (
    (sys.version_info[:2] == (2, 7) and sys.version_info >= (2, 7, 9)) or
    sys.version_info >= (3, 4, 3)
)

if _cookie_allows_colon_in_names and cookie_pickles_properly:
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

        if not _cookie_allows_colon_in_names:
            def load(self, rawdata):
                self.bad_cookies = set()
                if isinstance(rawdata, six.text_type):
                    rawdata = force_str(rawdata)
                super(SimpleCookie, self).load(rawdata)
                for key in self.bad_cookies:
                    del self[key]

            # override private __set() method:
            # (needed for using our Morsel, and for laxness with CookieError
            def _BaseCookie__set(self, key, real_value, coded_value):
                key = force_str(key)
                try:
                    M = self.get(key, Morsel())
                    M.set(key, real_value, coded_value)
                    dict.__setitem__(self, key, M)
                except http_cookies.CookieError:
                    if not hasattr(self, 'bad_cookies'):
                        self.bad_cookies = set()
                    self.bad_cookies.add(key)
                    dict.__setitem__(self, key, http_cookies.Morsel())


def parse_cookie(cookie):
    if cookie == '':
        return {}
    if not isinstance(cookie, http_cookies.BaseCookie):
        try:
            c = SimpleCookie()
            c.load(cookie)
        except http_cookies.CookieError:
            # Invalid cookie
            return {}
    else:
        c = cookie
    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict
