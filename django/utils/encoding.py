import codecs
import datetime
import locale
from decimal import Decimal
from urllib.parse import quote

from django.utils.functional import Promise


class DjangoUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        super().__init__(*args)

    def __str__(self):
        return "%s. You passed in %r (%s)" % (
            super().__str__(),
            self.obj,
            type(self.obj),
        )


def smart_str(s, encoding="utf-8", strings_only=False, errors="strict"):
    """
    Return a string representing 's'. Treat bytestrings using the 'encoding'
    codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_str(s, encoding, strings_only, errors)


_PROTECTED_TYPES = (
    type(None),
    int,
    float,
    Decimal,
    datetime.datetime,
    datetime.date,
    datetime.time,
)


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_str(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_str(s, encoding="utf-8", strings_only=False, errors="strict"):
    """
    Similar to smart_str(), except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), str):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if isinstance(s, bytes):
            s = str(s, encoding, errors)
        else:
            s = str(s)
    except UnicodeDecodeError as e:
        raise DjangoUnicodeDecodeError(s, *e.args)
    return s


def smart_bytes(s, encoding="utf-8", strings_only=False, errors="strict"):
    """
    Return a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_bytes(s, encoding, strings_only, errors)


def force_bytes(s, encoding="utf-8", strings_only=False, errors="strict"):
    """
    Similar to smart_bytes, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if isinstance(s, bytes):
        if encoding == "utf-8":
            return s
        else:
            return s.decode("utf-8", errors).encode(encoding, errors)
    if strings_only and is_protected_type(s):
        return s
    if isinstance(s, memoryview):
        return bytes(s)
    return str(s).encode(encoding, errors)


def iri_to_uri(iri):
    """
    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from RFC 3987 Section 3.1, slightly simplified since
    the input is assumed to be a string rather than an arbitrary byte stream.

    Take an IRI (string or UTF-8 bytes, e.g. '/I ♥ Django/' or
    b'/I \xe2\x99\xa5 Django/') and return a string containing the encoded
    result with ASCII chars only (e.g. '/I%20%E2%99%A5%20Django/').
    """
    # The list of safe characters here is constructed from the "reserved" and
    # "unreserved" characters specified in RFC 3986 Sections 2.2 and 2.3:
    #     reserved    = gen-delims / sub-delims
    #     gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    #     sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #                   / "*" / "+" / "," / ";" / "="
    #     unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # Of the unreserved characters, urllib.parse.quote() already considers all
    # but the ~ safe.
    # The % character is also added to the list of safe characters here, as the
    # end of RFC 3987 Section 3.1 specifically mentions that % must not be
    # converted.
    if iri is None:
        return iri
    elif isinstance(iri, Promise):
        iri = str(iri)
    return quote(iri, safe="/#%[]=:;$&()+,!?*@'~")


# List of byte values that uri_to_iri() decodes from percent encoding.
# First, the unreserved characters from RFC 3986:
_ascii_ranges = [[45, 46, 95, 126], range(65, 91), range(97, 123)]
_hextobyte = {
    (fmt % char).encode(): bytes((char,))
    for ascii_range in _ascii_ranges
    for char in ascii_range
    for fmt in ["%02x", "%02X"]
}
# And then everything above 128, because bytes ≥ 128 are part of multibyte
# Unicode characters.
_hexdig = "0123456789ABCDEFabcdef"
_hextobyte.update(
    {(a + b).encode(): bytes.fromhex(a + b) for a in _hexdig[8:] for b in _hexdig}
)


def uri_to_iri(uri):
    """
    Convert a Uniform Resource Identifier(URI) into an Internationalized
    Resource Identifier(IRI).

    This is the algorithm from RFC 3987 Section 3.2, excluding step 4.

    Take an URI in ASCII bytes (e.g. '/I%20%E2%99%A5%20Django/') and return
    a string containing the encoded result (e.g. '/I%20♥%20Django/').
    """
    if uri is None:
        return uri
    uri = force_bytes(uri)
    # Fast selective unquote: First, split on '%' and then starting with the
    # second block, decode the first 2 bytes if they represent a hex code to
    # decode. The rest of the block is the part after '%AB', not containing
    # any '%'. Add that to the output without further processing.
    bits = uri.split(b"%")
    if len(bits) == 1:
        iri = uri
    else:
        parts = [bits[0]]
        append = parts.append
        hextobyte = _hextobyte
        for item in bits[1:]:
            hex = item[:2]
            if hex in hextobyte:
                append(hextobyte[item[:2]])
                append(item[2:])
            else:
                append(b"%")
                append(item)
        iri = b"".join(parts)
    return repercent_broken_unicode(iri).decode()


def escape_uri_path(path):
    """
    Escape the unsafe characters from the path portion of a Uniform Resource
    Identifier (URI).
    """
    # These are the "reserved" and "unreserved" characters specified in RFC
    # 3986 Sections 2.2 and 2.3:
    #   reserved    = ";" | "/" | "?" | ":" | "@" | "&" | "=" | "+" | "$" | ","
    #   unreserved  = alphanum | mark
    #   mark        = "-" | "_" | "." | "!" | "~" | "*" | "'" | "(" | ")"
    # The list of safe characters here is constructed subtracting ";", "=",
    # and "?" according to RFC 3986 Section 3.3.
    # The reason for not subtracting and escaping "/" is that we are escaping
    # the entire path, not a path segment.
    return quote(path, safe="/:@&+$,-_.!~*'()")


def punycode(domain):
    """Return the Punycode of the given domain if it's non-ASCII."""
    return domain.encode("idna").decode("ascii")


def repercent_broken_unicode(path):
    """
    As per RFC 3987 Section 3.2, step three of converting a URI into an IRI,
    repercent-encode any octet produced that is not part of a strictly legal
    UTF-8 octet sequence.
    """
    while True:
        try:
            path.decode()
        except UnicodeDecodeError as e:
            # CVE-2019-14235: A recursion shouldn't be used since the exception
            # handling uses massive amounts of memory
            repercent = quote(path[e.start : e.end], safe=b"/#%[]=:;$&()+,!?*@'~")
            path = path[: e.start] + repercent.encode() + path[e.end :]
        else:
            return path


def filepath_to_uri(path):
    """Convert a file system path to a URI portion that is suitable for
    inclusion in a URL.

    Encode certain chars that would normally be recognized as special chars
    for URIs. Do not encode the ' character, as it is a valid character
    within URIs. See the encodeURIComponent() JavaScript function for details.
    """
    if path is None:
        return path
    # I know about `os.sep` and `os.altsep` but I want to leave
    # some flexibility for hardcoding separators.
    return quote(str(path).replace("\\", "/"), safe="/~!*()'")


def get_system_encoding():
    """
    The encoding for the character type functions. Fallback to 'ascii' if the
    #encoding is unsupported by Python or could not be determined. See tickets
    #10335 and #5846.
    """
    try:
        encoding = locale.getlocale()[1] or "ascii"
        codecs.lookup(encoding)
    except Exception:
        encoding = "ascii"
    return encoding


DEFAULT_LOCALE_ENCODING = get_system_encoding()
