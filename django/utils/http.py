import calendar
import datetime
import re
import sys
import urllib
import urlparse
from email.utils import formatdate

from django.utils.datastructures import MultiValueDict
from django.utils.encoding import smart_str, force_unicode
from django.utils.functional import allow_lazy

ETAG_MATCH = re.compile(r'(?:W/)?"((?:\\.|[^"])*)"')

MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
__D = r'(?P<day>\d{2})'
__D2 = r'(?P<day>[ \d]\d)'
__M = r'(?P<mon>\w{3})'
__Y = r'(?P<year>\d{4})'
__Y2 = r'(?P<year>\d{2})'
__T = r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})'
RFC1123_DATE = re.compile(r'^\w{3}, %s %s %s %s GMT$' % (__D, __M, __Y, __T))
RFC850_DATE = re.compile(r'^\w{6,9}, %s-%s-%s %s GMT$' % (__D, __M, __Y2, __T))
ASCTIME_DATE = re.compile(r'^\w{3} %s %s %s %s$' % (__M, __D2, __T, __Y))

def urlquote(url, safe='/'):
    """
    A version of Python's urllib.quote() function that can operate on unicode
    strings. The url is first UTF-8 encoded before quoting. The returned string
    can safely be used as part of an argument to a subsequent iri_to_uri() call
    without double-quoting occurring.
    """
    return force_unicode(urllib.quote(smart_str(url), smart_str(safe)))
urlquote = allow_lazy(urlquote, unicode)

def urlquote_plus(url, safe=''):
    """
    A version of Python's urllib.quote_plus() function that can operate on
    unicode strings. The url is first UTF-8 encoded before quoting. The
    returned string can safely be used as part of an argument to a subsequent
    iri_to_uri() call without double-quoting occurring.
    """
    return force_unicode(urllib.quote_plus(smart_str(url), smart_str(safe)))
urlquote_plus = allow_lazy(urlquote_plus, unicode)

def urlunquote(quoted_url):
    """
    A wrapper for Python's urllib.unquote() function that can operate on
    the result of django.utils.http.urlquote().
    """
    return force_unicode(urllib.unquote(smart_str(quoted_url)))
urlunquote = allow_lazy(urlunquote, unicode)

def urlunquote_plus(quoted_url):
    """
    A wrapper for Python's urllib.unquote_plus() function that can operate on
    the result of django.utils.http.urlquote_plus().
    """
    return force_unicode(urllib.unquote_plus(smart_str(quoted_url)))
urlunquote_plus = allow_lazy(urlunquote_plus, unicode)

def urlencode(query, doseq=0):
    """
    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings and
    then encoded as per normal.
    """
    if isinstance(query, MultiValueDict):
        query = query.lists()
    elif hasattr(query, 'items'):
        query = query.items()
    return urllib.urlencode(
        [(smart_str(k),
         isinstance(v, (list,tuple)) and [smart_str(i) for i in v] or smart_str(v))
            for k, v in query],
        doseq)

def cookie_date(epoch_seconds=None):
    """
    Formats the time to ensure compatibility with Netscape's cookie standard.

    Accepts a floating point number expressed in seconds since the epoch, in
    UTC - such as that outputted by time.time(). If set to None, defaults to
    the current time.

    Outputs a string in the format 'Wdy, DD-Mon-YYYY HH:MM:SS GMT'.
    """
    rfcdate = formatdate(epoch_seconds)
    return '%s-%s-%s GMT' % (rfcdate[:7], rfcdate[8:11], rfcdate[12:25])

def http_date(epoch_seconds=None):
    """
    Formats the time to match the RFC1123 date format as specified by HTTP
    RFC2616 section 3.3.1.

    Accepts a floating point number expressed in seconds since the epoch, in
    UTC - such as that outputted by time.time(). If set to None, defaults to
    the current time.

    Outputs a string in the format 'Wdy, DD Mon YYYY HH:MM:SS GMT'.
    """
    rfcdate = formatdate(epoch_seconds)
    return '%s GMT' % rfcdate[:25]

def parse_http_date(date):
    """
    Parses a date format as specified by HTTP RFC2616 section 3.3.1.

    The three formats allowed by the RFC are accepted, even if only the first
    one is still in widespread use.

    Returns an floating point number expressed in seconds since the epoch, in
    UTC.
    """
    # emails.Util.parsedate does the job for RFC1123 dates; unfortunately
    # RFC2616 makes it mandatory to support RFC850 dates too. So we roll
    # our own RFC-compliant parsing.
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            break
    else:
        raise ValueError("%r is not in a valid HTTP date format" % date)
    try:
        year = int(m.group('year'))
        if year < 100:
            if year < 70:
                year += 2000
            else:
                year += 1900
        month = MONTHS.index(m.group('mon').lower()) + 1
        day = int(m.group('day'))
        hour = int(m.group('hour'))
        min = int(m.group('min'))
        sec = int(m.group('sec'))
        result = datetime.datetime(year, month, day, hour, min, sec)
        return calendar.timegm(result.utctimetuple())
    except Exception:
        raise ValueError("%r is not a valid date" % date)

def parse_http_date_safe(date):
    """
    Same as parse_http_date, but returns None if the input is invalid.
    """
    try:
        return parse_http_date(date)
    except Exception:
        pass

# Base 36 functions: useful for generating compact URLs

def base36_to_int(s):
    """
    Converts a base 36 string to an ``int``. Raises ``ValueError` if the
    input won't fit into an int.
    """
    # To prevent overconsumption of server resources, reject any
    # base36 string that is long than 13 base36 digits (13 digits
    # is sufficient to base36-encode any 64-bit integer)
    if len(s) > 13:
        raise ValueError("Base36 input too large")
    value = int(s, 36)
    # ... then do a final check that the value will fit into an int.
    if value > sys.maxint:
        raise ValueError("Base36 input too large")
    return value

def int_to_base36(i):
    """
    Converts an integer to a base36 string
    """
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    factor = 0
    if not 0 <= i <= sys.maxint:
        raise ValueError("Base36 conversion input too large or incorrect type.")
    # Find starting factor
    while True:
        factor += 1
        if i < 36 ** factor:
            factor -= 1
            break
    base36 = []
    # Construct base36 representation
    while factor >= 0:
        j = 36 ** factor
        base36.append(digits[i // j])
        i = i % j
        factor -= 1
    return ''.join(base36)

def parse_etags(etag_str):
    """
    Parses a string with one or several etags passed in If-None-Match and
    If-Match headers by the rules in RFC 2616. Returns a list of etags
    without surrounding double quotes (") and unescaped from \<CHAR>.
    """
    etags = ETAG_MATCH.findall(etag_str)
    if not etags:
        # etag_str has wrong format, treat it as an opaque string then
        return [etag_str]
    etags = [e.decode('string_escape') for e in etags]
    return etags

def quote_etag(etag):
    """
    Wraps a string in double quotes escaping contents as necesary.
    """
    return '"%s"' % etag.replace('\\', '\\\\').replace('"', '\\"')

if sys.version_info >= (2, 6):
    def same_origin(url1, url2):
        """
        Checks if two URLs are 'same-origin'
        """
        p1, p2 = urlparse.urlparse(url1), urlparse.urlparse(url2)
        return (p1.scheme, p1.hostname, p1.port) == (p2.scheme, p2.hostname, p2.port)
else:
    # Python 2.5 compatibility. This actually works for Python 2.6 and above,
    # but the above definition is much more obviously correct and so is
    # preferred going forward.
    def same_origin(url1, url2):
        """
        Checks if two URLs are 'same-origin'
        """
        p1, p2 = urlparse.urlparse(url1), urlparse.urlparse(url2)
        return p1[0:2] == p2[0:2]

def is_safe_url(url, host=None):
    """
    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).

    Always returns ``False`` on an empty url.
    """
    if not url:
        return False
    # Chrome treats \ completely as /
    url = url.replace('\\', '/')
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlaprse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith('///'):
        return False
    url_info = urlparse.urlparse(url)
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info[1] and url_info[0]:
        return False
    return (not url_info[1] or url_info[1] == host) and \
        (not url_info[0] or url_info[0] in ['http', 'https'])
