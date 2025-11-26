import base64
import re
import unicodedata
from binascii import Error as BinasciiError
from datetime import datetime, timezone
from email.utils import formatdate
from urllib.parse import quote, unquote
from urllib.parse import urlencode as original_urlencode
from urllib.parse import urlparse

from django.utils.datastructures import MultiValueDict
from django.utils.regex_helper import _lazy_re_compile

# Based on RFC 9110 Appendix A.
ETAG_MATCH = _lazy_re_compile(
    r"""
    \A(      # start of string and capture group
    (?:W/)?  # optional weak indicator
    "        # opening quote
    [^"]*    # any sequence of non-quote characters
    "        # end quote
    )\Z      # end of string and capture group
""",
    re.X,
)

MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
__D = r"(?P<day>[0-9]{2})"
__D2 = r"(?P<day>[ 0-9][0-9])"
__M = r"(?P<mon>\w{3})"
__Y = r"(?P<year>[0-9]{4})"
__Y2 = r"(?P<year>[0-9]{2})"
__T = r"(?P<hour>[0-9]{2}):(?P<min>[0-9]{2}):(?P<sec>[0-9]{2})"
RFC1123_DATE = _lazy_re_compile(r"^\w{3}, %s %s %s %s GMT$" % (__D, __M, __Y, __T))
RFC850_DATE = _lazy_re_compile(r"^\w{6,9}, %s-%s-%s %s GMT$" % (__D, __M, __Y2, __T))
ASCTIME_DATE = _lazy_re_compile(r"^\w{3} %s %s %s %s$" % (__M, __D2, __T, __Y))

RFC3986_GENDELIMS = ":/?#[]@"
RFC3986_SUBDELIMS = "!$&'()*+,;="
MAX_URL_LENGTH = 2048
MAX_URL_REDIRECT_LENGTH = 16384


def urlencode(query, doseq=False):
    """
    A version of Python's urllib.parse.urlencode() function that can operate on
    MultiValueDict and non-string values.
    """
    if isinstance(query, MultiValueDict):
        query = query.lists()
    elif hasattr(query, "items"):
        query = query.items()
    query_params = []
    for key, value in query:
        if value is None:
            raise TypeError(
                "Cannot encode None for key '%s' in a query string. Did you "
                "mean to pass an empty string or omit the value?" % key
            )
        elif not doseq or isinstance(value, (str, bytes)):
            query_val = value
        else:
            try:
                itr = iter(value)
            except TypeError:
                query_val = value
            else:
                # Consume generators and iterators, when doseq=True, to
                # work around https://bugs.python.org/issue31706.
                query_val = []
                for item in itr:
                    if item is None:
                        raise TypeError(
                            "Cannot encode None for key '%s' in a query "
                            "string. Did you mean to pass an empty string or "
                            "omit the value?" % key
                        )
                    elif not isinstance(item, bytes):
                        item = str(item)
                    query_val.append(item)
        query_params.append((key, query_val))
    return original_urlencode(query_params, doseq)


def http_date(epoch_seconds=None):
    """
    Format the time to match the RFC 5322 date format as specified by RFC 9110
    Section 5.6.7.

    `epoch_seconds` is a floating point number expressed in seconds since the
    epoch, in UTC - such as that outputted by time.time(). If set to None, it
    defaults to the current time.

    Output a string in the format 'Wdy, DD Mon YYYY HH:MM:SS GMT'.
    """
    return formatdate(epoch_seconds, usegmt=True)


def parse_http_date(date):
    """
    Parse a date format as specified by HTTP RFC 9110 Section 5.6.7.

    The three formats allowed by the RFC are accepted, even if only the first
    one is still in widespread use.

    Return an integer expressed in seconds since the epoch, in UTC.
    """
    # email.utils.parsedate() does the job for RFC 1123 dates; unfortunately
    # RFC 9110 makes it mandatory to support RFC 850 dates too. So we roll
    # our own RFC-compliant parsing.
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            break
    else:
        raise ValueError("%r is not in a valid HTTP date format" % date)
    try:
        year = int(m["year"])
        if year < 100:
            current_year = datetime.now(tz=timezone.utc).year
            current_century = current_year - (current_year % 100)
            if year - (current_year % 100) > 50:
                # year that appears to be more than 50 years in the future are
                # interpreted as representing the past.
                year += current_century - 100
            else:
                year += current_century
        month = MONTHS.index(m["mon"].lower()) + 1
        day = int(m["day"])
        hour = int(m["hour"])
        min = int(m["min"])
        sec = int(m["sec"])
        result = datetime(year, month, day, hour, min, sec, tzinfo=timezone.utc)
        return int(result.timestamp())
    except Exception as exc:
        raise ValueError("%r is not a valid date" % date) from exc


def parse_http_date_safe(date):
    """
    Same as parse_http_date, but return None if the input is invalid.
    """
    try:
        return parse_http_date(date)
    except Exception:
        pass


# Base 36 functions: useful for generating compact URLs


def base36_to_int(s):
    """
    Convert a base 36 string to an int. Raise ValueError if the input won't fit
    into an int.
    """
    # To prevent overconsumption of server resources, reject any
    # base36 string that is longer than 13 base36 digits (13 digits
    # is sufficient to base36-encode any 64-bit integer)
    if len(s) > 13:
        raise ValueError("Base36 input too large")
    return int(s, 36)


def int_to_base36(i):
    """Convert an integer to a base36 string."""
    char_set = "0123456789abcdefghijklmnopqrstuvwxyz"
    if i < 0:
        raise ValueError("Negative base36 conversion input.")
    if i < 36:
        return char_set[i]
    b36 = ""
    while i != 0:
        i, n = divmod(i, 36)
        b36 = char_set[n] + b36
    return b36


def urlsafe_base64_encode(s):
    """
    Encode a bytestring to a base64 string for use in URLs. Strip any trailing
    equal signs.
    """
    return base64.urlsafe_b64encode(s).rstrip(b"\n=").decode("ascii")


def urlsafe_base64_decode(s):
    """
    Decode a base64 encoded string. Add back any trailing equal signs that
    might have been stripped.
    """
    s = s.encode()
    try:
        return base64.urlsafe_b64decode(s.ljust(len(s) + len(s) % 4, b"="))
    except (LookupError, BinasciiError) as e:
        raise ValueError(e)


def parse_etags(etag_str):
    """
    Parse a string of ETags given in an If-None-Match or If-Match header as
    defined by RFC 9110. Return a list of quoted ETags, or ['*'] if all ETags
    should be matched.
    """
    if etag_str.strip() == "*":
        return ["*"]
    else:
        # Parse each ETag individually, and return any that are valid.
        etag_matches = (ETAG_MATCH.match(etag.strip()) for etag in etag_str.split(","))
        return [match[1] for match in etag_matches if match]


def quote_etag(etag_str):
    """
    If the provided string is already a quoted ETag, return it. Otherwise, wrap
    the string in quotes, making it a strong ETag.
    """
    if ETAG_MATCH.match(etag_str):
        return etag_str
    else:
        return '"%s"' % etag_str


def is_same_domain(host, pattern):
    """
    Return ``True`` if the host is either an exact match or a match
    to the wildcard pattern.

    Any pattern beginning with a period matches a domain and all of its
    subdomains. (e.g. ``.example.com`` matches ``example.com`` and
    ``foo.example.com``). Anything else is an exact string match.
    """
    if not pattern:
        return False

    pattern = pattern.lower()
    return (
        pattern[0] == "."
        and (host.endswith(pattern) or host == pattern[1:])
        or pattern == host
    )


def url_has_allowed_host_and_scheme(url, allowed_hosts, require_https=False):
    """
    Return ``True`` if the url uses an allowed host and a safe scheme.

    Always return ``False`` on an empty url.

    If ``require_https`` is ``True``, only 'https' will be considered a valid
    scheme, as opposed to 'http' and 'https' with the default, ``False``.

    Note: "True" doesn't entail that a URL is "safe". It may still be e.g.
    quoted incorrectly. Ensure to also use django.utils.encoding.iri_to_uri()
    on the path component of untrusted URLs.
    """
    if url is not None:
        url = url.strip()
    if not url:
        return False
    if allowed_hosts is None:
        allowed_hosts = set()
    elif isinstance(allowed_hosts, str):
        allowed_hosts = {allowed_hosts}
    # Chrome treats \ completely as / in paths but it could be part of some
    # basic auth credentials so we need to check both URLs.
    return _url_has_allowed_host_and_scheme(
        url, allowed_hosts, require_https=require_https
    ) and _url_has_allowed_host_and_scheme(
        url.replace("\\", "/"), allowed_hosts, require_https=require_https
    )


def _url_has_allowed_host_and_scheme(url, allowed_hosts, require_https=False):
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlparse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith("///") or len(url) > MAX_URL_LENGTH:
        # urlparse does not perform validation of inputs. Unicode normalization
        # is very slow on Windows and can be a DoS attack vector.
        # https://docs.python.org/3/library/urllib.parse.html#url-parsing-security
        return False
    try:
        url_info = urlparse(url)
    except ValueError:  # e.g. invalid IPv6 addresses
        return False
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info.netloc and url_info.scheme:
        return False
    # Forbid URLs that start with control characters. Some browsers (like
    # Chrome) ignore quite a few control characters at the start of a
    # URL and might consider the URL as scheme relative.
    if unicodedata.category(url[0])[0] == "C":
        return False
    scheme = url_info.scheme
    # Consider URLs without a scheme (e.g. //example.com/p) to be http.
    if not url_info.scheme and url_info.netloc:
        scheme = "http"
    valid_schemes = ["https"] if require_https else ["http", "https"]
    return (not url_info.netloc or url_info.netloc in allowed_hosts) and (
        not scheme or scheme in valid_schemes
    )


def escape_leading_slashes(url):
    """
    If redirecting to an absolute path (two leading slashes), a slash must be
    escaped to prevent browsers from handling the path as schemaless and
    redirecting to another host.
    """
    if url.startswith("//"):
        url = "/%2F{}".format(url.removeprefix("//"))
    return url


def _parseparam(s):
    while s[:1] == ";":
        s = s[1:]
        end = s.find(";")
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(";", end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def parse_header_parameters(line):
    """
    Parse a Content-type like header.
    Return the main content-type and a dictionary of options.
    """
    parts = _parseparam(";" + line)
    key = parts.__next__().lower()
    pdict = {}
    for p in parts:
        i = p.find("=")
        if i >= 0:
            has_encoding = False
            name = p[:i].strip().lower()
            if name.endswith("*"):
                # Lang/encoding embedded in the value (like "filename*=UTF-8''file.ext")
                # https://tools.ietf.org/html/rfc2231#section-4
                name = name[:-1]
                if p.count("'") == 2:
                    has_encoding = True
            value = p[i + 1 :].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace("\\\\", "\\").replace('\\"', '"')
            if has_encoding:
                encoding, lang, value = value.split("'")
                value = unquote(value, encoding=encoding)
            pdict[name] = value
    return key, pdict


def content_disposition_header(as_attachment, filename):
    """
    Construct a Content-Disposition HTTP header value from the given filename
    as specified by RFC 6266.
    """
    if filename:
        disposition = "attachment" if as_attachment else "inline"
        try:
            filename.encode("ascii")
            file_expr = 'filename="{}"'.format(
                filename.replace("\\", "\\\\").replace('"', r"\"")
            )
        except UnicodeEncodeError:
            file_expr = "filename*=utf-8''{}".format(quote(filename))
        return f"{disposition}; {file_expr}"
    elif as_attachment:
        return "attachment"
    else:
        return None
