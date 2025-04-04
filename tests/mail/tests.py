import mimetypes
import os
import shutil
import socket
import sys
import tempfile
from email import charset, message_from_binary_file, message_from_bytes
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr
from io import StringIO
from pathlib import Path
from smtplib import SMTP, SMTPException
from ssl import SSLError
from unittest import mock, skipUnless

from django.core import mail
from django.core.mail import (
    DNS_NAME,
    BadHeaderError,
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
    mail_admins,
    mail_managers,
    send_mail,
    send_mass_mail,
)
from django.core.mail.backends import console, dummy, filebased, locmem, smtp
from django.core.mail.message import sanitize_address
from django.test import SimpleTestCase, override_settings
from django.test.utils import requires_tz_support
from django.utils.translation import gettext_lazy

try:
    from aiosmtpd.controller import Controller

    HAS_AIOSMTPD = True
except ImportError:
    HAS_AIOSMTPD = False


class HeadersCheckMixin:
    def assertMessageHasHeaders(self, message, headers):
        """
        Asserts that the `message` has all `headers`.

        message: can be an instance of an email.Message subclass or bytes
                 with the contents of an email message.
        headers: should be a set of (header-name, header-value) tuples.
        """
        if isinstance(message, bytes):
            message = message_from_bytes(message)
        msg_headers = set(message.items())
        self.assertTrue(
            headers.issubset(msg_headers),
            msg="Message is missing "
            "the following headers: %s" % (headers - msg_headers),
        )


class MailTests(HeadersCheckMixin, SimpleTestCase):
    """
    Non-backend specific tests.
    """

    def get_decoded_attachments(self, django_message):
        """
        Encode the specified django.core.mail.message.EmailMessage, then decode
        it using Python's email.parser module and, for each attachment of the
        message, return a list of tuples with (filename, content, mimetype).
        """
        msg_bytes = django_message.message().as_bytes()
        email_message = message_from_bytes(msg_bytes)

        def iter_attachments():
            for i in email_message.walk():
                if i.get_content_disposition() == "attachment":
                    filename = i.get_filename()
                    content = i.get_payload(decode=True)
                    mimetype = i.get_content_type()
                    yield filename, content, mimetype

        return list(iter_attachments())

    def test_ascii(self):
        email = EmailMessage(
            "Subject", "Content", "from@example.com", ["to@example.com"]
        )
        message = email.message()
        self.assertEqual(message["Subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content")
        self.assertEqual(message["From"], "from@example.com")
        self.assertEqual(message["To"], "to@example.com")

    @mock.patch("django.core.mail.message.MIMEText.set_payload")
    def test_nonascii_as_string_with_ascii_charset(self, mock_set_payload):
        """Line length check should encode the payload supporting `surrogateescape`.

        Following https://github.com/python/cpython/issues/76511, newer
        versions of Python (3.11.9, 3.12.3 and 3.13) ensure that a message's
        payload is encoded with the provided charset and `surrogateescape` is
        used as the error handling strategy.

        This test is heavily based on the test from the fix for the bug above.
        Line length checks in SafeMIMEText's set_payload should also use the
        same error handling strategy to avoid errors such as:

        UnicodeEncodeError: 'utf-8' codec can't encode <...>: surrogates not allowed

        """

        def simplified_set_payload(instance, payload, charset):
            instance._payload = payload

        mock_set_payload.side_effect = simplified_set_payload

        text = (
            "Text heavily based in Python's text for non-ascii messages: Föö bär"
        ).encode("iso-8859-1")
        body = text.decode("ascii", errors="surrogateescape")
        email = EmailMessage("Subject", body, "from@example.com", ["to@example.com"])
        message = email.message()
        mock_set_payload.assert_called_once()
        self.assertEqual(message.get_payload(decode=True), text)

    def test_multiple_recipients(self):
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com", "other@example.com"],
        )
        message = email.message()
        self.assertEqual(message["Subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content")
        self.assertEqual(message["From"], "from@example.com")
        self.assertEqual(message["To"], "to@example.com, other@example.com")

    def test_header_omitted_for_no_to_recipients(self):
        message = EmailMessage(
            "Subject", "Content", "from@example.com", cc=["cc@example.com"]
        ).message()
        self.assertNotIn("To", message)

    def test_recipients_with_empty_strings(self):
        """
        Empty strings in various recipient arguments are always stripped
        off the final recipient list.
        """
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com", ""],
            cc=["cc@example.com", ""],
            bcc=["", "bcc@example.com"],
            reply_to=["", None],
        )
        self.assertEqual(
            email.recipients(), ["to@example.com", "cc@example.com", "bcc@example.com"]
        )

    def test_cc(self):
        """Regression test for #7722"""
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com"],
            cc=["cc@example.com"],
        )
        message = email.message()
        self.assertEqual(message["Cc"], "cc@example.com")
        self.assertEqual(email.recipients(), ["to@example.com", "cc@example.com"])

        # Test multiple CC with multiple To
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com", "other@example.com"],
            cc=["cc@example.com", "cc.other@example.com"],
        )
        message = email.message()
        self.assertEqual(message["Cc"], "cc@example.com, cc.other@example.com")
        self.assertEqual(
            email.recipients(),
            [
                "to@example.com",
                "other@example.com",
                "cc@example.com",
                "cc.other@example.com",
            ],
        )

        # Testing with Bcc
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com", "other@example.com"],
            cc=["cc@example.com", "cc.other@example.com"],
            bcc=["bcc@example.com"],
        )
        message = email.message()
        self.assertEqual(message["Cc"], "cc@example.com, cc.other@example.com")
        self.assertEqual(
            email.recipients(),
            [
                "to@example.com",
                "other@example.com",
                "cc@example.com",
                "cc.other@example.com",
                "bcc@example.com",
            ],
        )

    def test_cc_headers(self):
        message = EmailMessage(
            "Subject",
            "Content",
            "bounce@example.com",
            ["to@example.com"],
            cc=["foo@example.com"],
            headers={"Cc": "override@example.com"},
        ).message()
        self.assertEqual(message.get_all("Cc"), ["override@example.com"])

    def test_cc_in_headers_only(self):
        message = EmailMessage(
            "Subject",
            "Content",
            "bounce@example.com",
            ["to@example.com"],
            headers={"Cc": "foo@example.com"},
        ).message()
        self.assertEqual(message.get_all("Cc"), ["foo@example.com"])

    def test_reply_to(self):
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com"],
            reply_to=["reply_to@example.com"],
        )
        message = email.message()
        self.assertEqual(message["Reply-To"], "reply_to@example.com")

        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com"],
            reply_to=["reply_to1@example.com", "reply_to2@example.com"],
        )
        message = email.message()
        self.assertEqual(
            message["Reply-To"], "reply_to1@example.com, reply_to2@example.com"
        )

    def test_recipients_as_tuple(self):
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ("to@example.com", "other@example.com"),
            cc=("cc@example.com", "cc.other@example.com"),
            bcc=("bcc@example.com",),
        )
        message = email.message()
        self.assertEqual(message["Cc"], "cc@example.com, cc.other@example.com")
        self.assertEqual(
            email.recipients(),
            [
                "to@example.com",
                "other@example.com",
                "cc@example.com",
                "cc.other@example.com",
                "bcc@example.com",
            ],
        )

    def test_recipients_as_string(self):
        with self.assertRaisesMessage(
            TypeError, '"to" argument must be a list or tuple'
        ):
            EmailMessage(to="foo@example.com")
        with self.assertRaisesMessage(
            TypeError, '"cc" argument must be a list or tuple'
        ):
            EmailMessage(cc="foo@example.com")
        with self.assertRaisesMessage(
            TypeError, '"bcc" argument must be a list or tuple'
        ):
            EmailMessage(bcc="foo@example.com")
        with self.assertRaisesMessage(
            TypeError, '"reply_to" argument must be a list or tuple'
        ):
            EmailMessage(reply_to="reply_to@example.com")

    def test_header_injection(self):
        msg = "Header values can't contain newlines "
        email = EmailMessage(
            "Subject\nInjection Test", "Content", "from@example.com", ["to@example.com"]
        )
        with self.assertRaisesMessage(BadHeaderError, msg):
            email.message()
        email = EmailMessage(
            gettext_lazy("Subject\nInjection Test"),
            "Content",
            "from@example.com",
            ["to@example.com"],
        )
        with self.assertRaisesMessage(BadHeaderError, msg):
            email.message()
        with self.assertRaisesMessage(BadHeaderError, msg):
            EmailMessage(
                "Subject",
                "Content",
                "from@example.com",
                ["Name\nInjection test <to@example.com>"],
            ).message()

    def test_folding_white_space(self):
        """
        Test for correct use of "folding white space" in long headers (#7747)
        """
        email = EmailMessage(
            "Long subject lines that get wrapped should contain a space continuation "
            "character to get expected behavior in Outlook and Thunderbird",
            "Content",
            "from@example.com",
            ["to@example.com"],
        )
        message = email.message()
        self.assertEqual(
            message["Subject"].encode(),
            b"Long subject lines that get wrapped should contain a space continuation\n"
            b" character to get expected behavior in Outlook and Thunderbird",
        )

    def test_message_header_overrides(self):
        """
        Specifying dates or message-ids in the extra headers overrides the
        default values (#9233)
        """
        headers = {"date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        email = EmailMessage(headers=headers)

        self.assertMessageHasHeaders(
            email.message(),
            {
                ("Message-ID", "foo"),
                ("date", "Fri, 09 Nov 2001 01:08:47 -0000"),
            },
        )

    def test_from_header(self):
        """
        Make sure we can manually set the From header (#9214)
        """
        email = EmailMessage(
            from_email="bounce@example.com",
            headers={"From": "from@example.com"},
        )
        message = email.message()
        self.assertEqual(message.get_all("From"), ["from@example.com"])

    def test_to_header(self):
        """
        Make sure we can manually set the To header (#17444)
        """
        email = EmailMessage(
            to=["list-subscriber@example.com", "list-subscriber2@example.com"],
            headers={"To": "mailing-list@example.com"},
        )
        message = email.message()
        self.assertEqual(message.get_all("To"), ["mailing-list@example.com"])
        self.assertEqual(
            email.to, ["list-subscriber@example.com", "list-subscriber2@example.com"]
        )

        # If we don't set the To header manually, it should default to the `to`
        # argument to the constructor.
        email = EmailMessage(
            to=["list-subscriber@example.com", "list-subscriber2@example.com"],
        )
        message = email.message()
        self.assertEqual(
            message.get_all("To"),
            ["list-subscriber@example.com, list-subscriber2@example.com"],
        )
        self.assertEqual(
            email.to, ["list-subscriber@example.com", "list-subscriber2@example.com"]
        )

    def test_to_in_headers_only(self):
        message = EmailMessage(
            headers={"To": "to@example.com"},
        ).message()
        self.assertEqual(message.get_all("To"), ["to@example.com"])

    def test_reply_to_header(self):
        """
        Specifying 'Reply-To' in headers should override reply_to.
        """
        email = EmailMessage(
            reply_to=["foo@example.com"],
            headers={"Reply-To": "override@example.com"},
        )
        message = email.message()
        self.assertEqual(message.get_all("Reply-To"), ["override@example.com"])

    def test_reply_to_in_headers_only(self):
        message = EmailMessage(
            headers={"Reply-To": "reply_to@example.com"},
        ).message()
        self.assertEqual(message.get_all("Reply-To"), ["reply_to@example.com"])

    def test_multiple_message_call(self):
        """
        Regression for #13259 - Make sure that headers are not changed when
        calling EmailMessage.message()
        """
        email = EmailMessage(
            from_email="bounce@example.com",
            headers={"From": "from@example.com"},
        )
        message = email.message()
        self.assertEqual(message.get_all("From"), ["from@example.com"])
        message = email.message()
        self.assertEqual(message.get_all("From"), ["from@example.com"])

    def test_unicode_address_header(self):
        """
        Regression for #11144 - When a to/from/cc header contains Unicode,
        make sure the email addresses are parsed correctly (especially with
        regards to commas)
        """
        email = EmailMessage(
            to=['"Firstname Sürname" <to@example.com>', "other@example.com"],
        )
        self.assertEqual(
            email.message()["To"],
            "=?utf-8?q?Firstname_S=C3=BCrname?= <to@example.com>, other@example.com",
        )

        email = EmailMessage(
            to=['"Sürname, Firstname" <to@example.com>', "other@example.com"],
        )
        self.assertEqual(
            email.message()["To"],
            "=?utf-8?q?S=C3=BCrname=2C_Firstname?= <to@example.com>, other@example.com",
        )

    def test_unicode_headers(self):
        email = EmailMessage(
            subject="Gżegżółka",
            to=["to@example.com"],
            headers={
                "Sender": '"Firstname Sürname" <sender@example.com>',
                "Comments": "My Sürname is non-ASCII",
            },
        )
        message = email.message()
        self.assertEqual(message["Subject"], "=?utf-8?b?R8W8ZWfFvMOzxYJrYQ==?=")
        self.assertEqual(
            message["Sender"], "=?utf-8?q?Firstname_S=C3=BCrname?= <sender@example.com>"
        )
        self.assertEqual(
            message["Comments"], "=?utf-8?q?My_S=C3=BCrname_is_non-ASCII?="
        )

    def test_non_utf8_headers_multipart(self):
        """
        Make sure headers can be set with a different encoding than utf-8 in
        EmailMultiAlternatives as well.
        """
        headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        from_email = "from@example.com"
        to = '"Sürname, Firstname" <to@example.com>'
        text_content = "This is an important message."
        html_content = "<p>This is an <strong>important</strong> message.</p>"
        msg = EmailMultiAlternatives(
            "Message from Firstname Sürname",
            text_content,
            from_email,
            [to],
            headers=headers,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.encoding = "iso-8859-1"
        self.assertEqual(
            msg.message()["To"],
            "=?iso-8859-1?q?S=FCrname=2C_Firstname?= <to@example.com>",
        )
        self.assertEqual(
            msg.message()["Subject"],
            "=?iso-8859-1?q?Message_from_Firstname_S=FCrname?=",
        )

    def test_multipart_with_attachments(self):
        """
        EmailMultiAlternatives includes alternatives if the body is empty and
        it has attachments.
        """
        msg = EmailMultiAlternatives(body="")
        html_content = "<p>This is <strong>html</strong></p>"
        msg.attach_alternative(html_content, "text/html")
        msg.attach("example.txt", "Text file content", "text/plain")
        self.assertIn(html_content, msg.message().as_string())

    def test_alternatives(self):
        msg = EmailMultiAlternatives()
        html_content = "<p>This is <strong>html</strong></p>"
        mime_type = "text/html"
        msg.attach_alternative(html_content, mime_type)

        self.assertIsInstance(msg.alternatives[0], EmailAlternative)

        self.assertEqual(msg.alternatives[0][0], html_content)
        self.assertEqual(msg.alternatives[0].content, html_content)

        self.assertEqual(msg.alternatives[0][1], mime_type)
        self.assertEqual(msg.alternatives[0].mimetype, mime_type)

        self.assertIn(html_content, msg.message().as_string())

    def test_alternatives_constructor(self):
        html_content = "<p>This is <strong>html</strong></p>"
        mime_type = "text/html"

        msg = EmailMultiAlternatives(
            alternatives=[EmailAlternative(html_content, mime_type)]
        )

        self.assertIsInstance(msg.alternatives[0], EmailAlternative)

        self.assertEqual(msg.alternatives[0][0], html_content)
        self.assertEqual(msg.alternatives[0].content, html_content)

        self.assertEqual(msg.alternatives[0][1], mime_type)
        self.assertEqual(msg.alternatives[0].mimetype, mime_type)

        self.assertIn(html_content, msg.message().as_string())

    def test_alternatives_constructor_from_tuple(self):
        html_content = "<p>This is <strong>html</strong></p>"
        mime_type = "text/html"

        msg = EmailMultiAlternatives(alternatives=[(html_content, mime_type)])

        self.assertIsInstance(msg.alternatives[0], EmailAlternative)

        self.assertEqual(msg.alternatives[0][0], html_content)
        self.assertEqual(msg.alternatives[0].content, html_content)

        self.assertEqual(msg.alternatives[0][1], mime_type)
        self.assertEqual(msg.alternatives[0].mimetype, mime_type)

        self.assertIn(html_content, msg.message().as_string())

    def test_none_body(self):
        msg = EmailMessage("subject", None, "from@example.com", ["to@example.com"])
        self.assertEqual(msg.body, "")
        self.assertEqual(msg.message().get_payload(), "")

    @mock.patch("socket.getfqdn", return_value="漢字")
    def test_non_ascii_dns_non_unicode_email(self, mocked_getfqdn):
        delattr(DNS_NAME, "_fqdn")
        email = EmailMessage()
        email.encoding = "iso-8859-1"
        self.assertIn("@xn--p8s937b>", email.message()["Message-ID"])

    def test_encoding(self):
        """
        Regression for #12791 - Encode body correctly with other encodings
        than utf-8
        """
        email = EmailMessage(body="Firstname Sürname is a great guy.")
        email.encoding = "iso-8859-1"
        message = email.message()
        self.assertMessageHasHeaders(
            message,
            {
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/plain; charset="iso-8859-1"'),
                ("Content-Transfer-Encoding", "quoted-printable"),
            },
        )
        self.assertEqual(message.get_payload(), "Firstname S=FCrname is a great guy.")

    def test_encoding_alternatives(self):
        """
        Encode alternatives correctly with other encodings than utf-8.
        """
        text_content = "Firstname Sürname is a great guy."
        html_content = "<p>Firstname Sürname is a <strong>great</strong> guy.</p>"
        email = EmailMultiAlternatives(body=text_content)
        email.encoding = "iso-8859-1"
        email.attach_alternative(html_content, "text/html")
        message = email.message()
        # Check the text/plain part.
        payload0 = message.get_payload(0)
        self.assertMessageHasHeaders(
            payload0,
            {
                # (The MIME-Version header is neither required nor meaningful
                # in a subpart, and this check for it can be safely removed.)
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/plain; charset="iso-8859-1"'),
                ("Content-Transfer-Encoding", "quoted-printable"),
            },
        )
        self.assertTrue(
            payload0.as_bytes().endswith(b"\n\nFirstname S=FCrname is a great guy.")
        )
        # Check the text/html alternative.
        payload1 = message.get_payload(1)
        self.assertMessageHasHeaders(
            payload1,
            {
                # (The MIME-Version header is neither required nor meaningful
                # in a subpart, and this check for it can be safely removed.)
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/html; charset="iso-8859-1"'),
                ("Content-Transfer-Encoding", "quoted-printable"),
            },
        )
        self.assertTrue(
            payload1.as_bytes().endswith(
                b"\n\n<p>Firstname S=FCrname is a <strong>great</strong> guy.</p>"
            )
        )

    def test_attachments(self):
        msg = EmailMessage()
        file_name = "example.txt"
        file_content = "Text file content"
        mime_type = "text/plain"
        msg.attach(file_name, file_content, mime_type)

        self.assertEqual(msg.attachments[0][0], file_name)
        self.assertEqual(msg.attachments[0].filename, file_name)

        self.assertEqual(msg.attachments[0][1], file_content)
        self.assertEqual(msg.attachments[0].content, file_content)

        self.assertEqual(msg.attachments[0][2], mime_type)
        self.assertEqual(msg.attachments[0].mimetype, mime_type)

        attachments = self.get_decoded_attachments(msg)
        self.assertEqual(attachments[0], (file_name, file_content.encode(), mime_type))

    def test_attachments_constructor(self):
        file_name = "example.txt"
        file_content = "Text file content"
        mime_type = "text/plain"
        msg = EmailMessage(
            attachments=[EmailAttachment(file_name, file_content, mime_type)]
        )

        self.assertIsInstance(msg.attachments[0], EmailAttachment)

        self.assertEqual(msg.attachments[0][0], file_name)
        self.assertEqual(msg.attachments[0].filename, file_name)

        self.assertEqual(msg.attachments[0][1], file_content)
        self.assertEqual(msg.attachments[0].content, file_content)

        self.assertEqual(msg.attachments[0][2], mime_type)
        self.assertEqual(msg.attachments[0].mimetype, mime_type)

        attachments = self.get_decoded_attachments(msg)
        self.assertEqual(attachments[0], (file_name, file_content.encode(), mime_type))

    def test_attachments_constructor_from_tuple(self):
        file_name = "example.txt"
        file_content = "Text file content"
        mime_type = "text/plain"
        msg = EmailMessage(attachments=[(file_name, file_content, mime_type)])

        self.assertIsInstance(msg.attachments[0], EmailAttachment)

        self.assertEqual(msg.attachments[0][0], file_name)
        self.assertEqual(msg.attachments[0].filename, file_name)

        self.assertEqual(msg.attachments[0][1], file_content)
        self.assertEqual(msg.attachments[0].content, file_content)

        self.assertEqual(msg.attachments[0][2], mime_type)
        self.assertEqual(msg.attachments[0].mimetype, mime_type)

        attachments = self.get_decoded_attachments(msg)
        self.assertEqual(attachments[0], (file_name, file_content.encode(), mime_type))

    def test_attachments_constructor_omit_mimetype(self):
        """
        The mimetype can be omitted from an attachment tuple.
        """
        msg = EmailMessage(attachments=[("filename1", "content1")])
        filename, content, mimetype = self.get_decoded_attachments(msg)[0]
        self.assertEqual(filename, "filename1")
        self.assertEqual(content, b"content1")
        self.assertEqual(mimetype, "application/octet-stream")

    def test_attachments_with_alternative_parts(self):
        """
        Message with attachment and alternative has correct structure (#9367).
        """
        text_content = "This is an important message."
        html_content = "<p>This is an <strong>important</strong> message.</p>"
        msg = EmailMultiAlternatives(body=text_content)
        msg.attach_alternative(html_content, "text/html")
        msg.attach("an attachment.pdf", b"%PDF-1.4.%...", mimetype="application/pdf")
        msg_bytes = msg.message().as_bytes()
        message = message_from_bytes(msg_bytes)
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_content_type(), "multipart/mixed")
        self.assertEqual(message.get_default_type(), "text/plain")
        payload = message.get_payload()
        self.assertEqual(payload[0].get_content_type(), "multipart/alternative")
        self.assertEqual(payload[1].get_content_type(), "application/pdf")

    def test_decoded_attachments_MIMEText(self):
        txt = MIMEText("content1")
        msg = EmailMessage(attachments=[txt])
        payload = msg.message().get_payload()
        self.assertEqual(payload[0], txt)

    def test_non_ascii_attachment_filename(self):
        """Regression test for #14964"""
        msg = EmailMessage(body="Content")
        # Unicode in file name
        msg.attach("une pièce jointe.pdf", b"%PDF-1.4.%...", mimetype="application/pdf")
        msg_bytes = msg.message().as_bytes()
        message = message_from_bytes(msg_bytes)
        payload = message.get_payload()
        self.assertEqual(payload[1].get_filename(), "une pièce jointe.pdf")

    def test_attach_file(self):
        """
        Test attaching a file against different mimetypes and make sure that
        a file will be attached and sent in some form even if a mismatched
        mimetype is specified.
        """
        files = (
            # filename, actual mimetype
            ("file.txt", "text/plain"),
            ("file.png", "image/png"),
            ("file_txt", None),
            ("file_png", None),
            ("file_txt.png", "image/png"),
            ("file_png.txt", "text/plain"),
            ("file.eml", "message/rfc822"),
        )
        test_mimetypes = ["text/plain", "image/png", None]

        for basename, real_mimetype in files:
            for mimetype in test_mimetypes:
                self.assertEqual(mimetypes.guess_type(basename)[0], real_mimetype)
                expected_mimetype = (
                    mimetype or real_mimetype or "application/octet-stream"
                )
                file_path = Path(__file__).parent / "attachments" / basename
                expected_content = file_path.read_bytes()
                if expected_mimetype.startswith("text/"):
                    try:
                        expected_content = expected_content.decode()
                    except UnicodeDecodeError:
                        expected_mimetype = "application/octet-stream"

                email = EmailMessage()
                email.attach_file(file_path, mimetype=mimetype)

                # Check EmailMessage.attachments.
                self.assertEqual(len(email.attachments), 1)
                self.assertEqual(email.attachments[0].filename, basename)
                self.assertEqual(email.attachments[0].mimetype, expected_mimetype)
                self.assertEqual(email.attachments[0].content, expected_content)

                # Check attachments in generated message.
                # (The actual content is not checked as variations in platform
                # line endings and rfc822 refolding complicate the logic.)
                actual_attachment = self.get_decoded_attachments(email)[0]
                actual_filename, actual_content, actual_mimetype = actual_attachment
                self.assertEqual(actual_filename, basename)
                self.assertEqual(actual_mimetype, expected_mimetype)

    def test_attach_text_as_bytes(self):
        msg = EmailMessage()
        msg.attach("file.txt", b"file content")
        filename, content, mimetype = self.get_decoded_attachments(msg)[0]
        self.assertEqual(filename, "file.txt")
        self.assertEqual(content, b"file content")
        self.assertEqual(mimetype, "text/plain")

    def test_attach_utf8_text_as_bytes(self):
        """
        Non-ASCII characters encoded as valid UTF-8 are correctly transported
        in a form that can be decoded at the receiving end.
        """
        msg = EmailMessage()
        msg.attach("file.txt", b"\xc3\xa4")  # UTF-8 encoded a umlaut.
        filename, content, mimetype = self.get_decoded_attachments(msg)[0]
        self.assertEqual(filename, "file.txt")
        self.assertEqual(content, b"\xc3\xa4")
        self.assertEqual(mimetype, "text/plain")

    def test_attach_non_utf8_text_as_bytes(self):
        """
        Binary data that can't be decoded as UTF-8 overrides the MIME type
        instead of decoding the data.
        """
        msg = EmailMessage()
        msg.attach("file.txt", b"\xff")  # Invalid UTF-8.
        filename, content, mimetype = self.get_decoded_attachments(msg)[0]
        self.assertEqual(filename, "file.txt")
        # Content should be passed through unmodified.
        self.assertEqual(content, b"\xff")
        self.assertEqual(mimetype, "application/octet-stream")

    def test_attach_mimebase_prohibits_other_params(self):
        email_msg = EmailMessage()
        txt = MIMEText("content")
        msg = (
            "content and mimetype must not be given when a MIMEBase instance "
            "is provided."
        )
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach(txt, content="content")
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach(txt, mimetype="text/plain")

    def test_attach_content_is_required(self):
        email_msg = EmailMessage()
        msg = "content must be provided."
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach("file.txt", mimetype="application/pdf")

    def test_dummy_backend(self):
        """
        Make sure that dummy backends returns correct number of sent messages
        """
        connection = dummy.EmailBackend()
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(connection.send_messages([email, email, email]), 3)

    def test_arbitrary_keyword(self):
        """
        Make sure that get_connection() accepts arbitrary keyword that might be
        used with custom backends.
        """
        c = mail.get_connection(fail_silently=True, foo="bar")
        self.assertTrue(c.fail_silently)

    def test_custom_backend(self):
        """Test custom backend defined in this suite."""
        conn = mail.get_connection("mail.custombackend.EmailBackend")
        self.assertTrue(hasattr(conn, "test_outbox"))
        email = EmailMessage(to=["to@example.com"])
        conn.send_messages([email])
        self.assertEqual(len(conn.test_outbox), 1)

    def test_backend_arg(self):
        """Test backend argument of mail.get_connection()"""
        self.assertIsInstance(
            mail.get_connection("django.core.mail.backends.smtp.EmailBackend"),
            smtp.EmailBackend,
        )
        self.assertIsInstance(
            mail.get_connection("django.core.mail.backends.locmem.EmailBackend"),
            locmem.EmailBackend,
        )
        self.assertIsInstance(
            mail.get_connection("django.core.mail.backends.dummy.EmailBackend"),
            dummy.EmailBackend,
        )
        self.assertIsInstance(
            mail.get_connection("django.core.mail.backends.console.EmailBackend"),
            console.EmailBackend,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.assertIsInstance(
                mail.get_connection(
                    "django.core.mail.backends.filebased.EmailBackend",
                    file_path=tmp_dir,
                ),
                filebased.EmailBackend,
            )

        msg = " not object"
        with self.assertRaisesMessage(TypeError, msg):
            mail.get_connection(
                "django.core.mail.backends.filebased.EmailBackend", file_path=object()
            )
        self.assertIsInstance(mail.get_connection(), locmem.EmailBackend)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ADMINS=[("nobody", "nobody@example.com")],
        MANAGERS=[("nobody", "nobody@example.com")],
    )
    def test_connection_arg(self):
        """Test connection argument to send_mail(), et. al."""
        mail.outbox = []

        # Send using non-default connection
        connection = mail.get_connection("mail.custombackend.EmailBackend")
        send_mail(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com"],
            connection=connection,
        )
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, "Subject")

        connection = mail.get_connection("mail.custombackend.EmailBackend")
        send_mass_mail(
            [
                ("Subject1", "Content1", "from1@example.com", ["to1@example.com"]),
                ("Subject2", "Content2", "from2@example.com", ["to2@example.com"]),
            ],
            connection=connection,
        )
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 2)
        self.assertEqual(connection.test_outbox[0].subject, "Subject1")
        self.assertEqual(connection.test_outbox[1].subject, "Subject2")

        connection = mail.get_connection("mail.custombackend.EmailBackend")
        mail_admins("Admin message", "Content", connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, "[Django] Admin message")

        connection = mail.get_connection("mail.custombackend.EmailBackend")
        mail_managers("Manager message", "Content", connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, "[Django] Manager message")

    def test_dont_mangle_from_in_body(self):
        # Regression for #13433 - Make sure that EmailMessage doesn't mangle
        # 'From ' in message body.
        email = EmailMessage(body="From the future")
        self.assertNotIn(b">From the future", email.message().as_bytes())

    def test_body_content_transfer_encoding(self):
        # Shouldn't use base64 or quoted-printable, instead should detect it
        # can represent content with 7-bit data (#3472, #11212).
        msg = EmailMessage(body="Body with only ASCII characters.")
        s = msg.message().as_bytes()
        self.assertIn(b"Content-Transfer-Encoding: 7bit", s)

        # Shouldn't use base64 or quoted-printable, instead should detect
        # it can represent content with 8-bit data.
        msg = EmailMessage(body="Body with latin characters: àáä.")
        s = msg.message().as_bytes()
        self.assertIn(b"Content-Transfer-Encoding: 8bit", s)
        # The following test is left over from Python 2 and can be safely removed.
        # 8bit CTE within a Unicode str is not meaningful, and Python's modern
        # email api won't generate it. (The test still works with the legacy api.)
        s = msg.message().as_string()
        self.assertIn("Content-Transfer-Encoding: 8bit", s)

        # Long body lines that require folding should use quoted-printable or base64,
        # whichever is shorter. However, Python's legacy email API avoids re-folding
        # non-ASCII text and just uses CTE 8bit. (The modern API would correctly choose
        # base64 here. Any of these is deliverable.)
        msg = EmailMessage(
            "Subject",
            "Body with non latin characters: А Б В Г Д Е Ж Ѕ З И І К Л М Н О П.",
            "bounce@example.com",
            ["to@example.com"],
            headers={"From": "from@example.com"},
        )
        s = msg.message().as_bytes()
        self.assertIn(b"Content-Transfer-Encoding: 8bit", s)
        # The following test is left over from Python 2.
        s = msg.message().as_string()
        self.assertIn("Content-Transfer-Encoding: 8bit", s)

    def test_dont_base64_encode_message_rfc822(self):
        # Ticket #18967
        # Shouldn't use base64 encoding for a child EmailMessage attachment.
        # Create a child message first
        child_msg = EmailMessage(
            "Child Subject",
            "Some body of child message",
            "bounce@example.com",
            ["to@example.com"],
            headers={"From": "from@example.com"},
        )
        child_s = child_msg.message().as_string()

        # Now create a parent
        parent_msg = EmailMessage(
            "Parent Subject",
            "Some parent body",
            "bounce@example.com",
            ["to@example.com"],
            headers={"From": "from@example.com"},
        )

        # Attach to parent as a string
        parent_msg.attach(content=child_s, mimetype="message/rfc822")
        parent_s = parent_msg.message().as_string()

        # The child message header is not base64 encoded
        self.assertIn("Child Subject", parent_s)

        # Feature test: try attaching email.Message object directly to the mail.
        parent_msg = EmailMessage(
            "Parent Subject",
            "Some parent body",
            "bounce@example.com",
            ["to@example.com"],
            headers={"From": "from@example.com"},
        )
        parent_msg.attach(content=child_msg.message(), mimetype="message/rfc822")
        parent_s = parent_msg.message().as_string()

        # The child message header is not base64 encoded
        self.assertIn("Child Subject", parent_s)

        # Feature test: try attaching Django's EmailMessage object directly to the mail.
        parent_msg = EmailMessage(
            "Parent Subject",
            "Some parent body",
            "bounce@example.com",
            ["to@example.com"],
            headers={"From": "from@example.com"},
        )
        parent_msg.attach(content=child_msg, mimetype="message/rfc822")
        parent_s = parent_msg.message().as_string()

        # The child message header is not base64 encoded
        self.assertIn("Child Subject", parent_s)

    def test_custom_utf8_encoding(self):
        """A UTF-8 charset with a custom body encoding is respected."""
        body = "Body with latin characters: àáä."
        msg = EmailMessage("Subject", body, "bounce@example.com", ["to@example.com"])
        encoding = charset.Charset("utf-8")
        encoding.body_encoding = charset.QP
        msg.encoding = encoding
        message = msg.message()
        self.assertMessageHasHeaders(
            message,
            {
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/plain; charset="utf-8"'),
                ("Content-Transfer-Encoding", "quoted-printable"),
            },
        )
        self.assertEqual(message.get_payload(), encoding.body_encode(body))

    def test_sanitize_address(self):
        """Email addresses are properly sanitized."""
        for email_address, encoding, expected_result in (
            # ASCII addresses.
            ("to@example.com", "ascii", "to@example.com"),
            ("to@example.com", "utf-8", "to@example.com"),
            (("A name", "to@example.com"), "ascii", "A name <to@example.com>"),
            (
                ("A name", "to@example.com"),
                "utf-8",
                "A name <to@example.com>",
            ),
            ("localpartonly", "ascii", "localpartonly"),
            # ASCII addresses with display names.
            ("A name <to@example.com>", "ascii", "A name <to@example.com>"),
            ("A name <to@example.com>", "utf-8", "A name <to@example.com>"),
            ('"A name" <to@example.com>', "ascii", "A name <to@example.com>"),
            ('"A name" <to@example.com>', "utf-8", "A name <to@example.com>"),
            # Unicode addresses: IDNA encoded domain supported per RFC-5890.
            ("to@éxample.com", "utf-8", "to@xn--xample-9ua.com"),
            # The next three cases should be removed when fixing #35713.
            # (An 'encoded-word' localpart is prohibited by RFC-2047, and not
            # supported by any known mail service.)
            ("tó@example.com", "utf-8", "=?utf-8?b?dMOz?=@example.com"),
            (
                ("Tó Example", "tó@example.com"),
                "utf-8",
                "=?utf-8?q?T=C3=B3_Example?= <=?utf-8?b?dMOz?=@example.com>",
            ),
            (
                "Tó Example <tó@example.com>",
                "utf-8",
                "=?utf-8?q?T=C3=B3_Example?= <=?utf-8?b?dMOz?=@example.com>",
            ),
            # IDNA addresses with display names.
            (
                "To Example <to@éxample.com>",
                "ascii",
                "To Example <to@xn--xample-9ua.com>",
            ),
            (
                "To Example <to@éxample.com>",
                "utf-8",
                "To Example <to@xn--xample-9ua.com>",
            ),
            # Addresses with two @ signs.
            ('"to@other.com"@example.com', "utf-8", r'"to@other.com"@example.com'),
            (
                '"to@other.com" <to@example.com>',
                "utf-8",
                '"to@other.com" <to@example.com>',
            ),
            (
                ("To Example", "to@other.com@example.com"),
                "utf-8",
                'To Example <"to@other.com"@example.com>',
            ),
            # Addresses with long unicode display names.
            (
                "Tó Example very long" * 4 + " <to@example.com>",
                "utf-8",
                "=?utf-8?q?T=C3=B3_Example_very_longT=C3=B3_Example_very_longT"
                "=C3=B3_Example_?=\n"
                " =?utf-8?q?very_longT=C3=B3_Example_very_long?= "
                "<to@example.com>",
            ),
            (
                ("Tó Example very long" * 4, "to@example.com"),
                "utf-8",
                "=?utf-8?q?T=C3=B3_Example_very_longT=C3=B3_Example_very_longT"
                "=C3=B3_Example_?=\n"
                " =?utf-8?q?very_longT=C3=B3_Example_very_long?= "
                "<to@example.com>",
            ),
            # Address with long display name and unicode domain.
            (
                ("To Example very long" * 4, "to@exampl€.com"),
                "utf-8",
                "To Example very longTo Example very longTo Example very longT"
                "o Example very\n"
                " long <to@xn--exampl-nc1c.com>",
            ),
        ):
            with self.subTest(email_address=email_address, encoding=encoding):
                self.assertEqual(
                    sanitize_address(email_address, encoding), expected_result
                )

    def test_sanitize_address_invalid(self):
        for email_address in (
            # Invalid address with two @ signs.
            "to@other.com@example.com",
            # Invalid address without the quotes.
            "to@other.com <to@example.com>",
            # Other invalid addresses.
            "@",
            "to@",
            "@example.com",
            ("", ""),
        ):
            with self.subTest(email_address=email_address):
                with self.assertRaisesMessage(ValueError, "Invalid address"):
                    sanitize_address(email_address, encoding="utf-8")

    def test_sanitize_address_header_injection(self):
        msg = "Invalid address; address parts cannot contain newlines."
        tests = [
            "Name\nInjection <to@example.com>",
            ("Name\nInjection", "to@xample.com"),
            "Name <to\ninjection@example.com>",
            ("Name", "to\ninjection@example.com"),
        ]
        for email_address in tests:
            with self.subTest(email_address=email_address):
                with self.assertRaisesMessage(ValueError, msg):
                    sanitize_address(email_address, encoding="utf-8")

    def test_email_multi_alternatives_content_mimetype_none(self):
        email_msg = EmailMultiAlternatives()
        msg = "Both content and mimetype must be provided."
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach_alternative(None, "text/html")
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach_alternative("<p>content</p>", None)

    def test_body_contains(self):
        email_msg = EmailMultiAlternatives()
        email_msg.body = "I am content."
        self.assertIs(email_msg.body_contains("I am"), True)
        self.assertIs(email_msg.body_contains("I am content."), True)

        email_msg.attach_alternative("<p>I am different content.</p>", "text/html")
        self.assertIs(email_msg.body_contains("I am"), True)
        self.assertIs(email_msg.body_contains("I am content."), False)
        self.assertIs(email_msg.body_contains("<p>I am different content.</p>"), False)

    def test_body_contains_alternative_non_text(self):
        email_msg = EmailMultiAlternatives()
        email_msg.body = "I am content."
        email_msg.attach_alternative("I am content.", "text/html")
        email_msg.attach_alternative(b"I am a song.", "audio/mpeg")
        self.assertIs(email_msg.body_contains("I am content"), True)


@requires_tz_support
class MailTimeZoneTests(SimpleTestCase):
    @override_settings(
        EMAIL_USE_LOCALTIME=False, USE_TZ=True, TIME_ZONE="Africa/Algiers"
    )
    def test_date_header_utc(self):
        """
        EMAIL_USE_LOCALTIME=False creates a datetime in UTC.
        """
        email = EmailMessage()
        self.assertTrue(email.message()["Date"].endswith("-0000"))

    @override_settings(
        EMAIL_USE_LOCALTIME=True, USE_TZ=True, TIME_ZONE="Africa/Algiers"
    )
    def test_date_header_localtime(self):
        """
        EMAIL_USE_LOCALTIME=True creates a datetime in the local time zone.
        """
        email = EmailMessage()
        self.assertTrue(
            email.message()["Date"].endswith("+0100")
        )  # Africa/Algiers is UTC+1


class PythonGlobalState(SimpleTestCase):
    """
    Tests for #12422 -- Django smarts (#2472/#11212) with charset of utf-8 text
    parts shouldn't pollute global email Python package charset registry when
    django.mail.message is imported.
    """

    def test_utf8(self):
        txt = MIMEText("UTF-8 encoded body", "plain", "utf-8")
        self.assertIn("Content-Transfer-Encoding: base64", txt.as_string())

    def test_7bit(self):
        txt = MIMEText("Body with only ASCII characters.", "plain", "utf-8")
        self.assertIn("Content-Transfer-Encoding: base64", txt.as_string())

    def test_8bit_latin(self):
        txt = MIMEText("Body with latin characters: àáä.", "plain", "utf-8")
        self.assertIn("Content-Transfer-Encoding: base64", txt.as_string())

    def test_8bit_non_latin(self):
        txt = MIMEText(
            "Body with non latin characters: А Б В Г Д Е Ж Ѕ З И І К Л М Н О П.",
            "plain",
            "utf-8",
        )
        self.assertIn("Content-Transfer-Encoding: base64", txt.as_string())


class BaseEmailBackendTests(HeadersCheckMixin):
    email_backend = None

    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(override_settings(EMAIL_BACKEND=cls.email_backend))
        super().setUpClass()

    def assertStartsWith(self, first, second):
        if not first.startswith(second):
            self.longMessage = True
            self.assertEqual(
                first[: len(second)],
                second,
                "First string doesn't start with the second.",
            )

    def get_mailbox_content(self):
        raise NotImplementedError(
            "subclasses of BaseEmailBackendTests must provide a get_mailbox_content() "
            "method"
        )

    def flush_mailbox(self):
        raise NotImplementedError(
            "subclasses of BaseEmailBackendTests may require a flush_mailbox() method"
        )

    def get_the_message(self):
        mailbox = self.get_mailbox_content()
        self.assertEqual(
            len(mailbox),
            1,
            "Expected exactly one message, got %d.\n%r"
            % (len(mailbox), [m.as_string() for m in mailbox]),
        )
        return mailbox[0]

    def test_send(self):
        email = EmailMessage(
            "Subject", "Content", "from@example.com", ["to@example.com"]
        )
        num_sent = mail.get_connection().send_messages([email])
        self.assertEqual(num_sent, 1)
        message = self.get_the_message()
        self.assertEqual(message["subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content")
        self.assertEqual(message["from"], "from@example.com")
        self.assertEqual(message.get_all("to"), ["to@example.com"])

    def test_send_unicode(self):
        email = EmailMessage(
            "Chère maman", "Je t'aime très fort", "from@example.com", ["to@example.com"]
        )
        num_sent = mail.get_connection().send_messages([email])
        self.assertEqual(num_sent, 1)
        message = self.get_the_message()
        self.assertEqual(message["subject"], "=?utf-8?q?Ch=C3=A8re_maman?=")
        self.assertEqual(
            message.get_payload(decode=True).decode(), "Je t'aime très fort"
        )

    def test_send_long_lines(self):
        """
        Email line length is limited to 998 chars by the RFC 5322 Section
        2.1.1.
        Message body containing longer lines are converted to Quoted-Printable
        to avoid having to insert newlines, which could be hairy to do properly.
        """
        # Unencoded body length is < 998 (840) but > 998 when utf-8 encoded.
        email = EmailMessage(
            "Subject", "В южных морях " * 60, "from@example.com", ["to@example.com"]
        )
        email.send()
        message = self.get_the_message()
        self.assertMessageHasHeaders(
            message,
            {
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/plain; charset="utf-8"'),
                ("Content-Transfer-Encoding", "quoted-printable"),
            },
        )

    def test_send_many(self):
        email1 = EmailMessage(to=["to-1@example.com"])
        email2 = EmailMessage(to=["to-2@example.com"])
        # send_messages() may take a list or an iterator.
        emails_lists = ([email1, email2], iter((email1, email2)))
        for emails_list in emails_lists:
            num_sent = mail.get_connection().send_messages(emails_list)
            self.assertEqual(num_sent, 2)
            messages = self.get_mailbox_content()
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["To"], "to-1@example.com")
            self.assertEqual(messages[1]["To"], "to-2@example.com")
            self.flush_mailbox()

    def test_send_verbose_name(self):
        email = EmailMessage(
            from_email='"Firstname Sürname" <from@example.com>',
            to=["to@example.com"],
        )
        email.send()
        message = self.get_the_message()
        self.assertEqual(
            message["from"], "=?utf-8?q?Firstname_S=C3=BCrname?= <from@example.com>"
        )

    def test_plaintext_send_mail(self):
        """
        Test send_mail without the html_message
        regression test for adding html_message parameter to send_mail()
        """
        send_mail("Subject", "Content", "sender@example.com", ["nobody@example.com"])
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertFalse(message.is_multipart())
        self.assertEqual(message.get_payload(), "Content")
        self.assertEqual(message.get_content_type(), "text/plain")

    def test_html_send_mail(self):
        """Test html_message argument to send_mail"""
        send_mail(
            "Subject",
            "Content",
            "sender@example.com",
            ["nobody@example.com"],
            html_message="HTML Content",
        )
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_payload(), "Content")
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_payload(), "HTML Content")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")

    @override_settings(MANAGERS=[("nobody", "nobody@example.com")])
    def test_html_mail_managers(self):
        """Test html_message argument to mail_managers"""
        mail_managers("Subject", "Content", html_message="HTML Content")
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "[Django] Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_payload(), "Content")
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_payload(), "HTML Content")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")

    @override_settings(ADMINS=[("nobody", "nobody@example.com")])
    def test_html_mail_admins(self):
        """Test html_message argument to mail_admins"""
        mail_admins("Subject", "Content", html_message="HTML Content")
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "[Django] Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_payload(), "Content")
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_payload(), "HTML Content")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")

    @override_settings(
        ADMINS=[("nobody", "nobody+admin@example.com")],
        MANAGERS=[("nobody", "nobody+manager@example.com")],
    )
    def test_manager_and_admin_mail_prefix(self):
        """
        String prefix + lazy translated subject = bad output
        Regression for #13494
        """
        mail_managers(gettext_lazy("Subject"), "Content")
        message = self.get_the_message()
        self.assertEqual(message.get("subject"), "[Django] Subject")

        self.flush_mailbox()
        mail_admins(gettext_lazy("Subject"), "Content")
        message = self.get_the_message()
        self.assertEqual(message.get("subject"), "[Django] Subject")

    @override_settings(ADMINS=[], MANAGERS=[])
    def test_empty_admins(self):
        """
        mail_admins/mail_managers doesn't connect to the mail server
        if there are no recipients (#9383)
        """
        mail_admins("hi", "there")
        self.assertEqual(self.get_mailbox_content(), [])
        mail_managers("hi", "there")
        self.assertEqual(self.get_mailbox_content(), [])

    def test_wrong_admins_managers(self):
        tests = (
            "test@example.com",
            ("test@example.com",),
            ["test@example.com", "other@example.com"],
            ("test@example.com", "other@example.com"),
        )
        for setting, mail_func in (
            ("ADMINS", mail_admins),
            ("MANAGERS", mail_managers),
        ):
            msg = "The %s setting must be a list of 2-tuples." % setting
            for value in tests:
                with (
                    self.subTest(setting=setting, value=value),
                    self.settings(**{setting: value}),
                ):
                    with self.assertRaisesMessage(ValueError, msg):
                        mail_func("subject", "content")

    def test_message_cc_header(self):
        """
        Regression test for #7722
        """
        email = EmailMessage(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com"],
            cc=["cc@example.com"],
        )
        mail.get_connection().send_messages([email])
        message = self.get_the_message()
        self.assertMessageHasHeaders(
            message,
            {
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/plain; charset="utf-8"'),
                ("Content-Transfer-Encoding", "7bit"),
                ("Subject", "Subject"),
                ("From", "from@example.com"),
                ("To", "to@example.com"),
                ("Cc", "cc@example.com"),
            },
        )
        self.assertIn("\nDate: ", message.as_string())

    def test_idn_send(self):
        """
        Regression test for #14301
        """
        self.assertTrue(send_mail("Subject", "Content", "from@öäü.com", ["to@öäü.com"]))
        message = self.get_the_message()
        self.assertEqual(message.get("from"), "from@xn--4ca9at.com")
        self.assertEqual(message.get("to"), "to@xn--4ca9at.com")

        self.flush_mailbox()
        m = EmailMessage(
            from_email="from@öäü.com", to=["to@öäü.com"], cc=["cc@öäü.com"]
        )
        m.send()
        message = self.get_the_message()
        self.assertEqual(message.get("from"), "from@xn--4ca9at.com")
        self.assertEqual(message.get("to"), "to@xn--4ca9at.com")
        self.assertEqual(message.get("cc"), "cc@xn--4ca9at.com")

    def test_recipient_without_domain(self):
        """
        Regression test for #15042
        """
        self.assertTrue(send_mail("Subject", "Content", "tester", ["django"]))
        message = self.get_the_message()
        self.assertEqual(message.get("from"), "tester")
        self.assertEqual(message.get("to"), "django")

    def test_lazy_addresses(self):
        """
        Email sending should support lazy email addresses (#24416).
        """
        _ = gettext_lazy
        self.assertTrue(send_mail("Subject", "Content", _("tester"), [_("django")]))
        message = self.get_the_message()
        self.assertEqual(message.get("from"), "tester")
        self.assertEqual(message.get("to"), "django")

        self.flush_mailbox()
        m = EmailMessage(
            from_email=_("tester"),
            to=[_("to1"), _("to2")],
            cc=[_("cc1"), _("cc2")],
            bcc=[_("bcc")],
            reply_to=[_("reply")],
        )
        self.assertEqual(m.recipients(), ["to1", "to2", "cc1", "cc2", "bcc"])
        m.send()
        message = self.get_the_message()
        self.assertEqual(message.get("from"), "tester")
        self.assertEqual(message.get("to"), "to1, to2")
        self.assertEqual(message.get("cc"), "cc1, cc2")
        self.assertEqual(message.get("Reply-To"), "reply")

    def test_close_connection(self):
        """
        Connection can be closed (even when not explicitly opened)
        """
        conn = mail.get_connection(username="", password="")
        conn.close()

    def test_use_as_contextmanager(self):
        """
        The connection can be used as a contextmanager.
        """
        opened = [False]
        closed = [False]
        conn = mail.get_connection(username="", password="")

        def open():
            opened[0] = True

        conn.open = open

        def close():
            closed[0] = True

        conn.close = close
        with conn as same_conn:
            self.assertTrue(opened[0])
            self.assertIs(same_conn, conn)
            self.assertFalse(closed[0])
        self.assertTrue(closed[0])


class LocmemBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = "django.core.mail.backends.locmem.EmailBackend"

    def get_mailbox_content(self):
        return [m.message() for m in mail.outbox]

    def flush_mailbox(self):
        mail.outbox = []

    def tearDown(self):
        super().tearDown()
        mail.outbox = []

    def test_locmem_shared_messages(self):
        """
        Make sure that the locmen backend populates the outbox.
        """
        connection = locmem.EmailBackend()
        connection2 = locmem.EmailBackend()
        email = EmailMessage(to=["to@example.com"])
        connection.send_messages([email])
        connection2.send_messages([email])
        self.assertEqual(len(mail.outbox), 2)

    def test_validate_multiline_headers(self):
        # Ticket #18861 - Validate emails when using the locmem backend
        with self.assertRaises(BadHeaderError):
            send_mail(
                "Subject\nMultiline", "Content", "from@example.com", ["to@example.com"]
            )

    def test_outbox_not_mutated_after_send(self):
        email = EmailMessage(
            subject="correct subject",
            to=["to@example.com"],
        )
        email.send()
        email.subject = "other subject"
        email.to.append("other@example.com")
        self.assertEqual(mail.outbox[0].subject, "correct subject")
        self.assertEqual(mail.outbox[0].to, ["to@example.com"])


class FileBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = "django.core.mail.backends.filebased.EmailBackend"

    def setUp(self):
        super().setUp()
        self.tmp_dir = self.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        _settings_override = override_settings(EMAIL_FILE_PATH=self.tmp_dir)
        _settings_override.enable()
        self.addCleanup(_settings_override.disable)

    def mkdtemp(self):
        return tempfile.mkdtemp()

    def flush_mailbox(self):
        for filename in os.listdir(self.tmp_dir):
            os.unlink(os.path.join(self.tmp_dir, filename))

    def get_mailbox_content(self):
        messages = []
        for filename in os.listdir(self.tmp_dir):
            with open(os.path.join(self.tmp_dir, filename), "rb") as fp:
                session = fp.read().split(b"\n" + (b"-" * 79) + b"\n")
            messages.extend(message_from_bytes(m) for m in session if m)
        return messages

    def test_file_sessions(self):
        """Make sure opening a connection creates a new file"""
        msg = EmailMessage(
            "Subject",
            "Content",
            "bounce@example.com",
            ["to@example.com"],
            headers={"From": "from@example.com"},
        )
        connection = mail.get_connection()
        connection.send_messages([msg])

        self.assertEqual(len(os.listdir(self.tmp_dir)), 1)
        with open(os.path.join(self.tmp_dir, os.listdir(self.tmp_dir)[0]), "rb") as fp:
            message = message_from_binary_file(fp)
        self.assertEqual(message.get_content_type(), "text/plain")
        self.assertEqual(message.get("subject"), "Subject")
        self.assertEqual(message.get("from"), "from@example.com")
        self.assertEqual(message.get("to"), "to@example.com")

        connection2 = mail.get_connection()
        connection2.send_messages([msg])
        self.assertEqual(len(os.listdir(self.tmp_dir)), 2)

        connection.send_messages([msg])
        self.assertEqual(len(os.listdir(self.tmp_dir)), 2)

        msg.connection = mail.get_connection()
        self.assertTrue(connection.open())
        msg.send()
        self.assertEqual(len(os.listdir(self.tmp_dir)), 3)
        msg.send()
        self.assertEqual(len(os.listdir(self.tmp_dir)), 3)

        connection.close()


class FileBackendPathLibTests(FileBackendTests):
    def mkdtemp(self):
        tmp_dir = super().mkdtemp()
        return Path(tmp_dir)


class ConsoleBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = "django.core.mail.backends.console.EmailBackend"

    def setUp(self):
        super().setUp()
        self.__stdout = sys.stdout
        self.stream = sys.stdout = StringIO()

    def tearDown(self):
        del self.stream
        sys.stdout = self.__stdout
        del self.__stdout
        super().tearDown()

    def flush_mailbox(self):
        self.stream = sys.stdout = StringIO()

    def get_mailbox_content(self):
        messages = self.stream.getvalue().split("\n" + ("-" * 79) + "\n")
        return [message_from_bytes(m.encode()) for m in messages if m]

    def test_console_stream_kwarg(self):
        """
        The console backend can be pointed at an arbitrary stream.
        """
        s = StringIO()
        connection = mail.get_connection(
            "django.core.mail.backends.console.EmailBackend", stream=s
        )
        send_mail(
            "Subject",
            "Content",
            "from@example.com",
            ["to@example.com"],
            connection=connection,
        )
        message = s.getvalue().split("\n" + ("-" * 79) + "\n")[0].encode()
        self.assertMessageHasHeaders(
            message,
            {
                ("MIME-Version", "1.0"),
                ("Content-Type", 'text/plain; charset="utf-8"'),
                ("Content-Transfer-Encoding", "7bit"),
                ("Subject", "Subject"),
                ("From", "from@example.com"),
                ("To", "to@example.com"),
            },
        )
        self.assertIn(b"\nDate: ", message)


class SMTPHandler:
    def __init__(self, *args, **kwargs):
        self.mailbox = []

    async def handle_DATA(self, server, session, envelope):
        data = envelope.content
        mail_from = envelope.mail_from

        message = message_from_bytes(data.rstrip())
        message_addr = parseaddr(message.get("from"))[1]
        if mail_from != message_addr:
            # According to the spec, mail_from does not necessarily match the
            # From header - this is the case where the local part isn't
            # encoded, so try to correct that.
            lp, domain = mail_from.split("@", 1)
            lp = Header(lp, "utf-8").encode()
            mail_from = "@".join([lp, domain])

        if mail_from != message_addr:
            return f"553 '{mail_from}' != '{message_addr}'"
        self.mailbox.append(message)
        return "250 OK"

    def flush_mailbox(self):
        self.mailbox[:] = []


@skipUnless(HAS_AIOSMTPD, "No aiosmtpd library detected.")
class SMTPBackendTestsBase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Find a free port.
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        cls.smtp_handler = SMTPHandler()
        cls.smtp_controller = Controller(
            cls.smtp_handler,
            hostname="127.0.0.1",
            port=port,
        )
        cls._settings_override = override_settings(
            EMAIL_HOST=cls.smtp_controller.hostname,
            EMAIL_PORT=cls.smtp_controller.port,
        )
        cls._settings_override.enable()
        cls.addClassCleanup(cls._settings_override.disable)
        cls.smtp_controller.start()
        cls.addClassCleanup(cls.stop_smtp)

    @classmethod
    def stop_smtp(cls):
        cls.smtp_controller.stop()


@skipUnless(HAS_AIOSMTPD, "No aiosmtpd library detected.")
class SMTPBackendTests(BaseEmailBackendTests, SMTPBackendTestsBase):
    email_backend = "django.core.mail.backends.smtp.EmailBackend"

    def setUp(self):
        super().setUp()
        self.smtp_handler.flush_mailbox()
        self.addCleanup(self.smtp_handler.flush_mailbox)

    def flush_mailbox(self):
        self.smtp_handler.flush_mailbox()

    def get_mailbox_content(self):
        return self.smtp_handler.mailbox

    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password",
    )
    def test_email_authentication_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.username, "not empty username")
        self.assertEqual(backend.password, "not empty password")

    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password",
    )
    def test_email_authentication_override_settings(self):
        backend = smtp.EmailBackend(username="username", password="password")
        self.assertEqual(backend.username, "username")
        self.assertEqual(backend.password, "password")

    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password",
    )
    def test_email_disabled_authentication(self):
        backend = smtp.EmailBackend(username="", password="")
        self.assertEqual(backend.username, "")
        self.assertEqual(backend.password, "")

    def test_auth_attempted(self):
        """
        Opening the backend with non empty username/password tries
        to authenticate against the SMTP server.
        """
        backend = smtp.EmailBackend(
            username="not empty username", password="not empty password"
        )
        with self.assertRaisesMessage(
            SMTPException, "SMTP AUTH extension not supported by server."
        ):
            with backend:
                pass

    def test_server_open(self):
        """
        open() returns whether it opened a connection.
        """
        backend = smtp.EmailBackend(username="", password="")
        self.assertIsNone(backend.connection)
        opened = backend.open()
        backend.close()
        self.assertIs(opened, True)

    def test_reopen_connection(self):
        backend = smtp.EmailBackend()
        # Simulate an already open connection.
        backend.connection = mock.Mock(spec=object())
        self.assertIs(backend.open(), False)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_tls)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_override_settings(self):
        backend = smtp.EmailBackend(use_tls=False)
        self.assertFalse(backend.use_tls)

    def test_email_tls_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertFalse(backend.use_tls)

    def test_ssl_tls_mutually_exclusive(self):
        msg = (
            "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
            "one of those settings to True."
        )
        with self.assertRaisesMessage(ValueError, msg):
            smtp.EmailBackend(use_ssl=True, use_tls=True)

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_ssl)

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_override_settings(self):
        backend = smtp.EmailBackend(use_ssl=False)
        self.assertFalse(backend.use_ssl)

    def test_email_ssl_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertFalse(backend.use_ssl)

    @override_settings(EMAIL_SSL_CERTFILE="foo")
    def test_email_ssl_certfile_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_certfile, "foo")

    @override_settings(EMAIL_SSL_CERTFILE="foo")
    def test_email_ssl_certfile_override_settings(self):
        backend = smtp.EmailBackend(ssl_certfile="bar")
        self.assertEqual(backend.ssl_certfile, "bar")

    def test_email_ssl_certfile_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertIsNone(backend.ssl_certfile)

    @override_settings(EMAIL_SSL_KEYFILE="foo")
    def test_email_ssl_keyfile_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_keyfile, "foo")

    @override_settings(EMAIL_SSL_KEYFILE="foo")
    def test_email_ssl_keyfile_override_settings(self):
        backend = smtp.EmailBackend(ssl_keyfile="bar")
        self.assertEqual(backend.ssl_keyfile, "bar")

    def test_email_ssl_keyfile_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertIsNone(backend.ssl_keyfile)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_attempts_starttls(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_tls)
        with self.assertRaisesMessage(
            SMTPException, "STARTTLS extension not supported by server."
        ):
            with backend:
                pass

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_attempts_ssl_connection(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_ssl)
        with self.assertRaises(SSLError):
            with backend:
                pass

    def test_connection_timeout_default(self):
        """The connection's timeout value is None by default."""
        connection = mail.get_connection("django.core.mail.backends.smtp.EmailBackend")
        self.assertIsNone(connection.timeout)

    def test_connection_timeout_custom(self):
        """The timeout parameter can be customized."""

        class MyEmailBackend(smtp.EmailBackend):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("timeout", 42)
                super().__init__(*args, **kwargs)

        myemailbackend = MyEmailBackend()
        myemailbackend.open()
        self.assertEqual(myemailbackend.timeout, 42)
        self.assertEqual(myemailbackend.connection.timeout, 42)
        myemailbackend.close()

    @override_settings(EMAIL_TIMEOUT=10)
    def test_email_timeout_override_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.timeout, 10)

    def test_email_msg_uses_crlf(self):
        """#23063 -- RFC-compliant messages are sent over SMTP."""
        send = SMTP.send
        try:
            smtp_messages = []

            def mock_send(self, s):
                smtp_messages.append(s)
                return send(self, s)

            SMTP.send = mock_send

            email = EmailMessage(
                "Subject", "Content", "from@example.com", ["to@example.com"]
            )
            mail.get_connection().send_messages([email])

            # Find the actual message
            msg = None
            for i, m in enumerate(smtp_messages):
                if m[:4] == "data":
                    msg = smtp_messages[i + 1]
                    break

            self.assertTrue(msg)

            msg = msg.decode()
            # The message only contains CRLF and not combinations of CRLF, LF, and CR.
            msg = msg.replace("\r\n", "")
            self.assertNotIn("\r", msg)
            self.assertNotIn("\n", msg)

        finally:
            SMTP.send = send

    def test_send_messages_after_open_failed(self):
        """
        send_messages() shouldn't try to send messages if open() raises an
        exception after initializing the connection.
        """
        backend = smtp.EmailBackend()
        # Simulate connection initialization success and a subsequent
        # connection exception.
        backend.connection = mock.Mock(spec=object())
        backend.open = lambda: None
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(backend.send_messages([email]), 0)

    def test_send_messages_empty_list(self):
        backend = smtp.EmailBackend()
        backend.connection = mock.Mock(spec=object())
        self.assertEqual(backend.send_messages([]), 0)

    def test_send_messages_zero_sent(self):
        """A message isn't sent if it doesn't have any recipients."""
        backend = smtp.EmailBackend()
        backend.connection = mock.Mock(spec=object())
        email = EmailMessage("Subject", "Content", "from@example.com", to=[])
        sent = backend.send_messages([email])
        self.assertEqual(sent, 0)


@skipUnless(HAS_AIOSMTPD, "No aiosmtpd library detected.")
class SMTPBackendStoppedServerTests(SMTPBackendTestsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = smtp.EmailBackend(username="", password="")
        cls.smtp_controller.stop()

    @classmethod
    def stop_smtp(cls):
        # SMTP controller is stopped in setUpClass().
        pass

    def test_server_stopped(self):
        """
        Closing the backend while the SMTP server is stopped doesn't raise an
        exception.
        """
        self.backend.close()

    def test_fail_silently_on_connection_error(self):
        """
        A socket connection error is silenced with fail_silently=True.
        """
        with self.assertRaises(ConnectionError):
            self.backend.open()
        self.backend.fail_silently = True
        self.backend.open()
