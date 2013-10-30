from __future__ import unicode_literals

from django.utils.encoding import force_str
from django.utils import six
from django.utils.six.moves import http_cookies


# Some versions of Python 2.7 and later won't need this encoding bug fix:
_cookie_encodes_correctly = http_cookies.SimpleCookie().value_encode(';') == (';', '"\\073"')
# See ticket #13007, http://bugs.python.org/issue2193 and http://trac.edgewall.org/ticket/2256
_tc = http_cookies.SimpleCookie()
try:
    _tc.load(str('foo:bar=1'))
    _cookie_allows_colon_in_names = True
except http_cookies.CookieError:
    _cookie_allows_colon_in_names = False

if _cookie_encodes_correctly and _cookie_allows_colon_in_names:
    SimpleCookie = http_cookies.SimpleCookie
else:
    Morsel = http_cookies.Morsel

    class SimpleCookie(http_cookies.SimpleCookie):
        if not _cookie_encodes_correctly:
            def value_encode(self, val):
                # Some browsers do not support quoted-string from RFC 2109,
                # including some versions of Safari and Internet Explorer.
                # These browsers split on ';', and some versions of Safari
                # are known to split on ', '. Therefore, we encode ';' and ','

                # SimpleCookie already does the hard work of encoding and decoding.
                # It uses octal sequences like '\\012' for newline etc.
                # and non-ASCII chars. We just make use of this mechanism, to
                # avoid introducing two encoding schemes which would be confusing
                # and especially awkward for javascript.

                # NB, contrary to Python docs, value_encode returns a tuple containing
                # (real val, encoded_val)
                val, encoded = super(SimpleCookie, self).value_encode(val)

                encoded = encoded.replace(";", "\\073").replace(",", "\\054")
                # If encoded now contains any quoted chars, we need double quotes
                # around the whole string.
                if "\\" in encoded and not encoded.startswith('"'):
                    encoded = '"' + encoded + '"'

                return val, encoded

        if not _cookie_allows_colon_in_names:
            def load(self, rawdata):
                self.bad_cookies = set()
                if six.PY2 and isinstance(rawdata, six.text_type):
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
