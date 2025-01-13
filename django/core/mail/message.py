import email.message
import email.policy
import mimetypes
import warnings
from collections import namedtuple
from datetime import datetime, timezone
from email.headerregistry import Address, AddressHeader
from email.mime.base import MIMEBase
from email.utils import make_msgid
from pathlib import Path

from django.conf import settings
from django.core.mail._deprecated import (  # NOQA: F401; RemovedInDjango61Warning
    forbid_multi_line_headers,
    sanitize_address,
)
from django.core.mail.utils import DNS_NAME
from django.utils.deprecation import RemovedInDjango61Warning
from django.utils.encoding import force_bytes, force_str, punycode
from django.utils.timezone import get_current_timezone

# Default MIME type to use on attachments (if it is not explicitly given
# and cannot be guessed).
DEFAULT_ATTACHMENT_MIME_TYPE = "application/octet-stream"

EmailAlternative = namedtuple("Alternative", ["content", "mimetype"])
EmailAttachment = namedtuple("Attachment", ["filename", "content", "mimetype"])


class EmailMessage:
    """A container for email information."""

    content_subtype = "plain"

    # Undocumented charset to use for text/* message bodies
    # and attachments. Defaults to settings.DEFAULT_CHARSET.
    # (Should rename to `charset` if it will be documented.)
    encoding = None  # None => use settings default

    def __init__(
        self,
        subject="",
        body="",
        from_email=None,
        to=None,
        bcc=None,
        connection=None,
        attachments=None,
        headers=None,
        cc=None,
        reply_to=None,
    ):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).
        """
        if to:
            if isinstance(to, str):
                raise TypeError('"to" argument must be a list or tuple')
            self.to = list(to)
        else:
            self.to = []
        if cc:
            if isinstance(cc, str):
                raise TypeError('"cc" argument must be a list or tuple')
            self.cc = list(cc)
        else:
            self.cc = []
        if bcc:
            if isinstance(bcc, str):
                raise TypeError('"bcc" argument must be a list or tuple')
            self.bcc = list(bcc)
        else:
            self.bcc = []
        if reply_to:
            if isinstance(reply_to, str):
                raise TypeError('"reply_to" argument must be a list or tuple')
            self.reply_to = list(reply_to)
        else:
            self.reply_to = []
        self.from_email = from_email or settings.DEFAULT_FROM_EMAIL
        self.subject = subject
        self.body = body or ""
        self.attachments = []
        if attachments:
            for attachment in attachments:
                # RemovedInDjango61Warning: MIMEBase attachment support.
                if isinstance(attachment, (MIMEBase, email.message.MIMEPart)):
                    self.attach(attachment)
                else:
                    self.attach(*attachment)
        self.extra_headers = headers or {}
        self.connection = connection

    def get_connection(self, fail_silently=False):
        from django.core.mail import get_connection

        if not self.connection:
            self.connection = get_connection(fail_silently=fail_silently)
        return self.connection

    def message(self, *, policy=email.policy.default):
        msg = email.message.EmailMessage(policy=policy)
        self._add_bodies(msg)
        self._add_attachments(msg)

        msg["Subject"] = str(self.subject)
        msg["From"] = str(self.extra_headers.get("From", self.from_email))
        self._set_list_header_if_not_empty(msg, "To", self.to)
        self._set_list_header_if_not_empty(msg, "Cc", self.cc)
        self._set_list_header_if_not_empty(msg, "Reply-To", self.reply_to)

        # Email header names are case-insensitive (RFC 2045), so we have to
        # accommodate that when doing comparisons.
        header_names = [key.lower() for key in self.extra_headers]
        if "date" not in header_names:
            if settings.EMAIL_USE_LOCALTIME:
                tz = get_current_timezone()
            else:
                tz = timezone.utc
            msg["Date"] = datetime.now(tz)
        if "message-id" not in header_names:
            # Use cached DNS_NAME for performance
            msg["Message-ID"] = make_msgid(domain=DNS_NAME)
        for name, value in self.extra_headers.items():
            # Avoid headers handled above.
            if name.lower() not in {"from", "to", "cc", "reply-to"}:
                msg[name] = force_str(value, strings_only=True)
        self._idna_encode_address_header_domains(msg)
        return msg

    def recipients(self):
        """
        Return a list of all recipients of the email (includes direct
        addressees as well as Cc and Bcc entries).
        """
        return [email for email in (self.to + self.cc + self.bcc) if email]

    def send(self, fail_silently=False):
        """Send the email message."""
        if not self.recipients():
            # Don't bother creating the network connection if there's nobody to
            # send to.
            return 0
        return self.get_connection(fail_silently).send_messages([self])

    def attach(self, filename=None, content=None, mimetype=None):
        """
        Attach a file with the given filename and content. The filename can
        be omitted and the mimetype is guessed, if not provided.

        If the first parameter is a MIMEBase subclass, insert it directly
        into the resulting message attachments.

        For a text/* mimetype (guessed or specified), when a bytes object is
        specified as content, decode it as UTF-8. If that fails, set the
        mimetype to DEFAULT_ATTACHMENT_MIME_TYPE and don't decode the content.
        """
        if isinstance(filename, email.message.MIMEPart):
            if content is not None or mimetype is not None:
                raise ValueError(
                    "content and mimetype must not be given when a MIMEPart "
                    "instance is provided."
                )
            self.attachments.append(filename)
        elif isinstance(filename, MIMEBase):
            warnings.warn(
                "MIMEBase attachments are deprecated."
                " Use an email.message.MIMEPart instead.",
                RemovedInDjango61Warning,
            )
            if content is not None or mimetype is not None:
                raise ValueError(
                    "content and mimetype must not be given when a MIMEBase "
                    "instance is provided."
                )
            self.attachments.append(filename)
        elif content is None:
            raise ValueError("content must be provided.")
        else:
            mimetype = (
                mimetype
                or mimetypes.guess_type(filename)[0]
                or DEFAULT_ATTACHMENT_MIME_TYPE
            )
            basetype, subtype = mimetype.split("/", 1)

            if basetype == "text":
                if isinstance(content, bytes):
                    try:
                        content = content.decode()
                    except UnicodeDecodeError:
                        # If mimetype suggests the file is text but it's
                        # actually binary, read() raises a UnicodeDecodeError.
                        mimetype = DEFAULT_ATTACHMENT_MIME_TYPE

            self.attachments.append(EmailAttachment(filename, content, mimetype))

    def attach_file(self, path, mimetype=None):
        """
        Attach a file from the filesystem.

        Set the mimetype to DEFAULT_ATTACHMENT_MIME_TYPE if it isn't specified
        and cannot be guessed.

        For a text/* mimetype (guessed or specified), decode the file's content
        as UTF-8. If that fails, set the mimetype to
        DEFAULT_ATTACHMENT_MIME_TYPE and don't decode the content.
        """
        path = Path(path)
        with path.open("rb") as file:
            content = file.read()
            self.attach(path.name, content, mimetype)

    def _add_bodies(self, msg):
        if self.body or not self.attachments:
            encoding = self.encoding or settings.DEFAULT_CHARSET
            body = force_str(
                self.body or "", encoding=encoding, errors="surrogateescape"
            )
            msg.set_content(body, subtype=self.content_subtype, charset=encoding)

    def _add_attachments(self, msg):
        if self.attachments:
            if hasattr(self, "mixed_subtype"):
                # RemovedInDjango61Warning
                raise AttributeError(
                    "EmailMessage no longer supports the"
                    " undocumented `mixed_subtype` attribute"
                )
            msg.make_mixed()
            for attachment in self.attachments:
                if isinstance(attachment, email.message.MIMEPart):
                    msg.attach(attachment)
                elif isinstance(attachment, MIMEBase):
                    # RemovedInDjango61Warning
                    msg.attach(attachment)
                else:
                    self._add_attachment(msg, *attachment)

    def _add_attachment(self, msg, filename, content, mimetype):
        encoding = self.encoding or settings.DEFAULT_CHARSET
        if mimetype is None:
            mimetype = DEFAULT_ATTACHMENT_MIME_TYPE
        maintype, subtype = mimetype.split("/", 1)
        # See email.contentmanager.set_content() docs for the cases here.
        if maintype == "text":
            # For text/*, content must be str, and maintype cannot be provided.
            if isinstance(content, bytes):
                content = content.decode()
            msg.add_attachment(
                content, subtype=subtype, filename=filename, charset=encoding
            )
        elif maintype == "message":
            # For message/*, content must be email.message.EmailMessage (or
            # legacy email.message.Message), and maintype cannot be provided.
            if isinstance(content, EmailMessage):
                # Django EmailMessage.
                content = content.message(policy=msg.policy)
            elif not isinstance(
                content, (email.message.EmailMessage, email.message.Message)
            ):
                content = email.message_from_bytes(
                    force_bytes(content), policy=msg.policy
                )
            msg.add_attachment(content, subtype=subtype, filename=filename)
        else:
            # For all other types, content must be bytes-like, and both
            # maintype and subtype must be provided.
            if not isinstance(content, (bytes, bytearray, memoryview)):
                content = force_bytes(content)
            msg.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )

    def _set_list_header_if_not_empty(self, msg, header, values):
        """
        Set msg's header, either from self.extra_headers, if present, or from
        the values argument if not empty.
        """
        try:
            msg[header] = self.extra_headers[header]
        except KeyError:
            if values:
                msg[header] = ", ".join(str(v) for v in values)

    def _idna_encode_address_header_domains(self, msg):
        """
        If msg.policy does not permit utf8 in headers, IDNA encode all non-ASCII
        domains in its address headers.
        """
        # Avoids a problem where Python's email incorrectly converts non-ASCII domains
        # to RFC 2047 encoded-words: https://github.com/python/cpython/issues/83938.
        # This applies to the domain only, not to the localpart (username). There is no
        # RFC that permits any 7-bit encoding for non-ASCII characters before the '@'.
        if not getattr(msg.policy, "utf8", False):
            # Not using SMTPUTF8, so apply IDNA encoding in all address headers.
            # (IDNA encoding does not alter domains that are already ASCII.)
            for field, value in msg.items():
                if isinstance(value, AddressHeader) and any(
                    not addr.domain.isascii() for addr in value.addresses
                ):
                    msg.replace_header(
                        field,
                        [
                            Address(
                                display_name=addr.display_name,
                                username=addr.username,
                                domain=punycode(addr.domain),
                            )
                            for addr in value.addresses
                        ],
                    )


class EmailMultiAlternatives(EmailMessage):
    """
    A version of EmailMessage that makes it easy to send multipart/alternative
    messages. For example, including text and HTML versions of the text is
    made easier.
    """

    def __init__(
        self,
        subject="",
        body="",
        from_email=None,
        to=None,
        bcc=None,
        connection=None,
        attachments=None,
        headers=None,
        alternatives=None,
        cc=None,
        reply_to=None,
    ):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).
        """
        super().__init__(
            subject,
            body,
            from_email,
            to,
            bcc,
            connection,
            attachments,
            headers,
            cc,
            reply_to,
        )
        self.alternatives = [
            EmailAlternative(*alternative) for alternative in (alternatives or [])
        ]

    def attach_alternative(self, content, mimetype):
        """Attach an alternative content representation."""
        if content is None or mimetype is None:
            raise ValueError("Both content and mimetype must be provided.")
        self.alternatives.append(EmailAlternative(content, mimetype))

    def _add_bodies(self, msg):
        if self.body or not self.alternatives:
            super()._add_bodies(msg)
        if self.alternatives:
            if hasattr(self, "alternative_subtype"):
                # RemovedInDjango61Warning
                raise AttributeError(
                    "EmailMultiAlternatives no longer supports the"
                    " undocumented `alternative_subtype` attribute"
                )
            msg.make_alternative()
            encoding = self.encoding or settings.DEFAULT_CHARSET
            for alternative in self.alternatives:
                maintype, subtype = alternative.mimetype.split("/", 1)
                content = alternative.content
                if maintype == "text":
                    if isinstance(content, bytes):
                        content = content.decode()
                    msg.add_alternative(content, subtype=subtype, charset=encoding)
                else:
                    content = force_bytes(content, encoding=encoding, strings_only=True)
                    msg.add_alternative(content, maintype=maintype, subtype=subtype)
        return msg

    def body_contains(self, text):
        """
        Checks that ``text`` occurs in the email body and in all attached MIME
        type text/* alternatives.
        """
        if text not in self.body:
            return False

        for content, mimetype in self.alternatives:
            if mimetype.startswith("text/") and text not in content:
                return False
        return True
