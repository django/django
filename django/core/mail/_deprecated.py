# RemovedInDjango70Warning: This entire file.
import warnings
from email import charset as Charset
from email import generator
from email.errors import HeaderParseError
from email.header import Header
from email.headerregistry import Address, parser
from email.mime.message import MIMEMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, getaddresses
from io import BytesIO, StringIO

from django.conf import settings
from django.utils.deprecation import RemovedInDjango70Warning
from django.utils.encoding import force_str, punycode

# Don't BASE64-encode UTF-8 messages so that we avoid unwanted attention from
# some spam filters.
utf8_charset = Charset.Charset("utf-8")
utf8_charset.body_encoding = None  # Python defaults to BASE64
utf8_charset_qp = Charset.Charset("utf-8")
utf8_charset_qp.body_encoding = Charset.QP

RFC5322_EMAIL_LINE_LENGTH_LIMIT = 998


# BadHeaderError must _be_ ValueError (not subclass it), so that existing code
# with `except BadHeaderError` will catch the ValueError that Python's modern
# email API raises for headers containing CR or NL.
BadHeaderError = ValueError

# Header names that contain structured address data (RFC 5322).
ADDRESS_HEADERS = {
    "from",
    "sender",
    "reply-to",
    "to",
    "cc",
    "bcc",
    "resent-from",
    "resent-sender",
    "resent-to",
    "resent-cc",
    "resent-bcc",
}


def forbid_multi_line_headers(name, val, encoding):
    """Forbid multi-line headers to prevent header injection."""
    warnings.warn(
        "The internal API forbid_multi_line_headers() is deprecated."
        " Python's modern email API (with email.message.EmailMessage or"
        " email.policy.default) will reject multi-line headers.",
        RemovedInDjango70Warning,
    )

    encoding = encoding or settings.DEFAULT_CHARSET
    val = str(val)  # val may be lazy
    if "\n" in val or "\r" in val:
        raise BadHeaderError(
            "Header values can't contain newlines (got %r for header %r)" % (val, name)
        )
    try:
        val.encode("ascii")
    except UnicodeEncodeError:
        if name.lower() in ADDRESS_HEADERS:
            val = ", ".join(
                sanitize_address(addr, encoding) for addr in getaddresses((val,))
            )
        else:
            val = Header(val, encoding).encode()
    else:
        if name.lower() == "subject":
            val = Header(val).encode()
    return name, val


def sanitize_address(addr, encoding):
    """
    Format a pair of (name, address) or an email address string.
    """
    warnings.warn(
        "The internal API sanitize_address() is deprecated."
        " Python's modern email API (with email.message.EmailMessage or"
        " email.policy.default) will handle most required validation and"
        " encoding. Use Python's email.headerregistry.Address to construct"
        " formatted addresses from component parts.",
        RemovedInDjango70Warning,
    )

    address = None
    if not isinstance(addr, tuple):
        addr = force_str(addr)
        try:
            token, rest = parser.get_mailbox(addr)
        except (HeaderParseError, ValueError, IndexError):
            raise ValueError('Invalid address "%s"' % addr)
        else:
            if rest:
                # The entire email address must be parsed.
                raise ValueError(
                    'Invalid address; only %s could be parsed from "%s"' % (token, addr)
                )
            nm = token.display_name or ""
            localpart = token.local_part
            domain = token.domain or ""
    else:
        nm, address = addr
        if "@" not in address:
            raise ValueError(f'Invalid address "{address}"')
        localpart, domain = address.rsplit("@", 1)

    address_parts = nm + localpart + domain
    if "\n" in address_parts or "\r" in address_parts:
        raise ValueError("Invalid address; address parts cannot contain newlines.")

    # Avoid UTF-8 encode, if it's possible.
    try:
        nm.encode("ascii")
        nm = Header(nm).encode()
    except UnicodeEncodeError:
        nm = Header(nm, encoding).encode()
    try:
        localpart.encode("ascii")
    except UnicodeEncodeError:
        localpart = Header(localpart, encoding).encode()
    domain = punycode(domain)

    parsed_address = Address(username=localpart, domain=domain)
    return formataddr((nm, parsed_address.addr_spec))


class MIMEMixin:
    def as_string(self, unixfrom=False, linesep="\n"):
        """Return the entire formatted message as a string.
        Optional `unixfrom' when True, means include the Unix From_ envelope
        header.

        This overrides the default as_string() implementation to not mangle
        lines that begin with 'From '. See bug #13433 for details.
        """
        fp = StringIO()
        g = generator.Generator(fp, mangle_from_=False)
        g.flatten(self, unixfrom=unixfrom, linesep=linesep)
        return fp.getvalue()

    def as_bytes(self, unixfrom=False, linesep="\n"):
        """Return the entire formatted message as bytes.
        Optional `unixfrom' when True, means include the Unix From_ envelope
        header.

        This overrides the default as_bytes() implementation to not mangle
        lines that begin with 'From '. See bug #13433 for details.
        """
        fp = BytesIO()
        g = generator.BytesGenerator(fp, mangle_from_=False)
        g.flatten(self, unixfrom=unixfrom, linesep=linesep)
        return fp.getvalue()


class SafeMIMEMessage(MIMEMixin, MIMEMessage):
    def __setitem__(self, name, val):
        # message/rfc822 attachments must be ASCII
        name, val = forbid_multi_line_headers(name, val, "ascii")
        MIMEMessage.__setitem__(self, name, val)


class SafeMIMEText(MIMEMixin, MIMEText):
    def __init__(self, _text, _subtype="plain", _charset=None):
        self.encoding = _charset
        MIMEText.__init__(self, _text, _subtype=_subtype, _charset=_charset)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEText.__setitem__(self, name, val)

    def set_payload(self, payload, charset=None):
        if charset == "utf-8" and not isinstance(charset, Charset.Charset):
            has_long_lines = any(
                len(line.encode(errors="surrogateescape"))
                > RFC5322_EMAIL_LINE_LENGTH_LIMIT
                for line in payload.splitlines()
            )
            # Quoted-Printable encoding has the side effect of shortening long
            # lines, if any (#22561).
            charset = utf8_charset_qp if has_long_lines else utf8_charset
        MIMEText.set_payload(self, payload, charset=charset)


class SafeMIMEMultipart(MIMEMixin, MIMEMultipart):
    def __init__(
        self, _subtype="mixed", boundary=None, _subparts=None, encoding=None, **_params
    ):
        self.encoding = encoding
        MIMEMultipart.__init__(self, _subtype, boundary, _subparts, **_params)

    def __setitem__(self, name, val):
        name, val = forbid_multi_line_headers(name, val, self.encoding)
        MIMEMultipart.__setitem__(self, name, val)
