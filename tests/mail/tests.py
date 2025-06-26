import ast
import mimetypes
import os
import pickle
import re
import shutil
import socket
import sys
import tempfile
from datetime import datetime, timezone
from email import message_from_binary_file
from email import message_from_bytes as _message_from_bytes
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage as PyEmailMessage
from email.message import Message as PyMessage
from email.message import MIMEPart
from io import StringIO
from pathlib import Path
from smtplib import SMTP, SMTPException
from ssl import SSLError
from textwrap import dedent
from unittest import mock, skipUnless

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import (
    DNS_NAME,
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
from django.test import SimpleTestCase, override_settings
from django.test.utils import requires_tz_support
from django.utils.translation import gettext_lazy

try:
    from aiosmtpd.controller import Controller

    HAS_AIOSMTPD = True
except ImportError:
    HAS_AIOSMTPD = False


def message_from_bytes(s):
    """
    email.message_from_bytes() using modern email.policy.default.
    Returns a modern email.message.EmailMessage.
    """
    # The modern email parser has a bug with adjacent rfc2047 encoded-words.
    # This doesn't affect django.core.mail (which doesn't parse messages),
    # but it can confuse our tests that try to verify sent content by reparsing
    # the generated message. Apply a workaround if needed.
    message = _message_from_bytes(s, policy=policy.default)
    if _needs_cpython_128110_workaround and _rfc2047_prefix_bytes in s:
        _apply_cpython_128110_workaround(message, s)
    return message


class MailTestsMixin:
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
        if not headers.issubset(msg_headers):
            missing = "\n".join(f"  {h}: {v}" for h, v in headers - msg_headers)
            actual = "\n".join(f"  {h}: {v}" for h, v in msg_headers)
            raise self.failureException(
                f"Expected headers not found in message.\n"
                f"Missing headers:\n{missing}\n"
                f"Actual headers:\n{actual}"
            )

    # In assertStartsWith()/assertEndsWith() failure messages, when truncating
    # a long first ("haystack") string, include this many characters beyond the
    # length of the second ("needle") string.
    START_END_EXTRA_CONTEXT = 15

    def assertStartsWith(self, first, second):
        if not first.startswith(second):
            # Use assertEqual() for failure message with diffs. If first value
            # is much longer than second, truncate end and add an ellipsis.
            self.longMessage = True
            max_len = len(second) + self.START_END_EXTRA_CONTEXT
            start_of_first = (
                first
                if len(first) <= max_len
                else first[:max_len] + ("…" if isinstance(first, str) else b"...")
            )
            self.assertEqual(
                start_of_first,
                second,
                "First string doesn't start with the second.",
            )

    def assertEndsWith(self, first, second):
        if not first.endswith(second):
            # Use assertEqual() for failure message with diffs. If first value
            # is much longer than second, truncate start and prepend an ellipsis.
            self.longMessage = True
            max_len = len(second) + self.START_END_EXTRA_CONTEXT
            end_of_first = (
                first
                if len(first) <= max_len
                else ("…" if isinstance(first, str) else b"...") + first[-max_len:]
            )
            self.assertEqual(
                end_of_first,
                second,
                "First string doesn't end with the second.",
            )

    def get_raw_attachments(self, django_message):
        """
        Return a list of the raw attachment parts in the MIME message generated
        by serializing django_message and reparsing the result.

        This returns only "top-level" attachments. It will not descend into
        message/* attached emails to find nested attachments.
        """
        msg_bytes = django_message.message().as_bytes()
        message = message_from_bytes(msg_bytes)
        return list(message.iter_attachments())

    def get_decoded_attachments(self, django_message):
        """
        Return a list of decoded attachments resulting from serializing
        django_message and reparsing the result.

        Each attachment is returned as an EmailAttachment named tuple with
        fields filename, content, and mimetype. The content will be decoded
        to str for mimetype text/*; retained as bytes for other mimetypes.
        """
        return [
            EmailAttachment(
                attachment.get_filename(),
                attachment.get_content(),
                attachment.get_content_type(),
            )
            for attachment in self.get_raw_attachments(django_message)
        ]

    def get_message_structure(self, message, level=0):
        """
        Return a multiline indented string representation
        of the message's MIME content-type structure, e.g.:

            multipart/mixed
                multipart/alternative
                    text/plain
                    text/html
                image/jpg
                text/calendar
        """
        # Adapted from email.iterators._structure().
        indent = " " * (level * 4)
        structure = [f"{indent}{message.get_content_type()}\n"]
        if message.is_multipart():
            for subpart in message.get_payload():
                structure.append(self.get_message_structure(subpart, level + 1))
        return "".join(structure)


class MailTests(MailTestsMixin, SimpleTestCase):
    """
    Non-backend specific tests.
    """

    def test_ascii(self):
        email = EmailMessage(
            "Subject", "Content\n", "from@example.com", ["to@example.com"]
        )
        message = email.message()
        self.assertEqual(message["Subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content\n")
        self.assertEqual(message["From"], "from@example.com")
        self.assertEqual(message["To"], "to@example.com")

    def test_multiple_recipients(self):
        email = EmailMessage(
            "Subject",
            "Content\n",
            "from@example.com",
            ["to@example.com", "other@example.com"],
        )
        message = email.message()
        self.assertEqual(message["Subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content\n")
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

    def test_bcc_not_in_headers(self):
        """
        A bcc address should be in the recipients,
        but not in the (visible) message headers.
        """
        email = EmailMessage(
            to=["to@example.com"],
            bcc=["bcc@example.com"],
        )
        message = email.message()
        self.assertNotIn("Bcc", message)
        self.assertNotIn("bcc@example.com", message.as_string())
        self.assertEqual(email.recipients(), ["to@example.com", "bcc@example.com"])

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
        msg = "Header values may not contain linefeed or carriage return characters"
        cases = [
            {"subject": "Subject\nInjection Test"},
            {"subject": gettext_lazy("Lazy Subject\nInjection Test")},
            {"to": ["Name\nInjection test <to@example.com>"]},
        ]
        for kwargs in cases:
            with self.subTest(case=kwargs):
                email = EmailMessage(**kwargs)
                with self.assertRaisesMessage(ValueError, msg):
                    email.message()

    def test_folding_white_space(self):
        """
        Test for correct use of "folding white space" in long headers (#7747)
        """
        email = EmailMessage(
            "Long subject lines that get wrapped should contain a space continuation "
            "character to comply with RFC 822",
        )
        message = email.message()
        msg_bytes = message.as_bytes()
        self.assertIn(
            b"Subject: Long subject lines that get wrapped should contain a space\n"
            b" continuation character to comply with RFC 822",
            msg_bytes,
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

    def test_datetime_in_date_header(self):
        """
        A datetime in headers should be passed through to Python email intact,
        so that it uses the email header date format.
        """
        email = EmailMessage(
            headers={"Date": datetime(2001, 11, 9, 1, 8, 47, tzinfo=timezone.utc)},
        )
        message = email.message()
        self.assertEqual(message["Date"], "Fri, 09 Nov 2001 01:08:47 +0000")
        # Not the default ISO format from force_str(strings_only=False).
        self.assertNotEqual(message["Date"], "2001-11-09 01:08:47+00:00")

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
        parsed = message_from_bytes(email.message().as_bytes())
        self.assertEqual(
            parsed["To"].addresses,
            (
                Address(display_name="Firstname Sürname", addr_spec="to@example.com"),
                Address(addr_spec="other@example.com"),
            ),
        )

        email = EmailMessage(
            to=['"Sürname, Firstname" <to@example.com>', "other@example.com"],
        )
        parsed = message_from_bytes(email.message().as_bytes())
        self.assertEqual(
            parsed["To"].addresses,
            (
                Address(display_name="Sürname, Firstname", addr_spec="to@example.com"),
                Address(addr_spec="other@example.com"),
            ),
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

        # Verify sent headers use RFC 2047 encoded-words (not raw utf-8).
        # The exact encoding details don't matter so long as the result parses
        # to the original values.
        msg_bytes = message.as_bytes()
        self.assertTrue(msg_bytes.isascii())  # not unencoded utf-8.
        parsed = message_from_bytes(msg_bytes)
        self.assertEqual(parsed["Subject"], "Gżegżółka")
        self.assertEqual(
            parsed["Sender"].address,
            Address(display_name="Firstname Sürname", addr_spec="sender@example.com"),
        )
        self.assertEqual(parsed["Comments"], "My Sürname is non-ASCII")

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
        email = EmailMultiAlternatives(
            "Message from Firstname Sürname",
            text_content,
            from_email,
            [to],
            headers=headers,
        )
        email.attach_alternative(html_content, "text/html")
        email.encoding = "iso-8859-1"
        message = email.message()

        # Verify sent headers use RFC 2047 encoded-words, not raw utf-8.
        msg_bytes = message.as_bytes()
        self.assertTrue(msg_bytes.isascii())

        # Verify sent headers parse to original values.
        parsed = message_from_bytes(msg_bytes)
        self.assertEqual(parsed["Subject"], "Message from Firstname Sürname")
        self.assertEqual(
            parsed["To"].addresses,
            (Address(display_name="Sürname, Firstname", addr_spec="to@example.com"),),
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

    def test_alternative_alternatives(self):
        """
        Alternatives can be attached as either string or bytes
        and need not use a text/* mimetype.
        """
        cases = [
            # (mimetype, content, expected decoded payload)
            ("application/x-ccmail-rtf", b"non-text\x07bytes", b"non-text\x07bytes"),
            ("application/x-ccmail-rtf", "non-text\x07string", b"non-text\x07string"),
            ("text/x-amp-html", b"text bytes\n", b"text bytes\n"),
            ("text/x-amp-html", "text string\n", b"text string\n"),
        ]
        for mimetype, content, expected in cases:
            email = EmailMultiAlternatives()
            email.attach_alternative(content, mimetype)
            msg = email.message()
            self.assertEqual(msg.get_content_type(), "multipart/alternative")
            alternative = msg.get_payload()[0]
            self.assertEqual(alternative.get_content_type(), mimetype)
            self.assertEqual(alternative.get_payload(decode=True), expected)

    def test_alternatives_and_attachment_serializable(self):
        html_content = "<p>This is <strong>html</strong></p>"
        mime_type = "text/html"

        msg = EmailMultiAlternatives(alternatives=[(html_content, mime_type)])
        msg.attach("test.txt", "This is plain text.", "plain/text")

        # Alternatives and attachments can be serialized.
        restored = pickle.loads(pickle.dumps(msg))

        self.assertEqual(restored.subject, msg.subject)
        self.assertEqual(restored.body, msg.body)
        self.assertEqual(restored.from_email, msg.from_email)
        self.assertEqual(restored.to, msg.to)
        self.assertEqual(restored.alternatives, msg.alternatives)
        self.assertEqual(restored.attachments, msg.attachments)

    def test_none_body(self):
        msg = EmailMessage("subject", None, "from@example.com", ["to@example.com"])
        self.assertEqual(msg.body, "")
        # The modern email API forces trailing newlines on all text/* parts,
        # even an empty body.
        self.assertEqual(msg.message().get_payload(), "\n")

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
        email = EmailMessage(body="Firstname Sürname is a great guy.\n")
        email.encoding = "iso-8859-1"
        message = email.message()
        self.assertEqual(message["Content-Type"], 'text/plain; charset="iso-8859-1"')

        # Check that body is actually encoded with iso-8859-1.
        msg_bytes = message.as_bytes()
        if message["Content-Transfer-Encoding"] == "quoted-printable":
            self.assertIn(b"Firstname S=FCrname is a great guy.", msg_bytes)
        elif message["Content-Transfer-Encoding"] == "8bit":
            self.assertIn(b"Firstname S\xfc", msg_bytes)
        else:
            self.fail("Unexpected Content-Transfer-Encoding")

        parsed = message_from_bytes(msg_bytes)
        self.assertEqual(parsed.get_content(), "Firstname Sürname is a great guy.\n")

    def test_encoding_alternatives(self):
        """
        Encode alternatives correctly with other encodings than utf-8.
        """
        text_content = "Firstname Sürname is a great guy.\n"
        html_content = "<p>Firstname Sürname is a <strong>great</strong> guy.</p>\n"
        email = EmailMultiAlternatives(body=text_content)
        email.encoding = "iso-8859-1"
        email.attach_alternative(html_content, "text/html")
        message = email.message()
        # Check both parts are sent using the specified encoding.
        self.assertEqual(
            message.get_payload(0)["Content-Type"], 'text/plain; charset="iso-8859-1"'
        )
        self.assertEqual(
            message.get_payload(1)["Content-Type"], 'text/html; charset="iso-8859-1"'
        )

        # Check both parts decode to the original content at the receiving end.
        parsed = message_from_bytes(message.as_bytes())
        self.assertEqual(parsed.get_body(("plain",)).get_content(), text_content)
        self.assertEqual(parsed.get_body(("html",)).get_content(), html_content)

    def test_attachments(self):
        msg = EmailMessage()
        file_name = "example.txt"
        file_content = "Text file content\n"
        mime_type = "text/plain"
        msg.attach(file_name, file_content, mime_type)

        self.assertEqual(msg.attachments[0][0], file_name)
        self.assertEqual(msg.attachments[0].filename, file_name)

        self.assertEqual(msg.attachments[0][1], file_content)
        self.assertEqual(msg.attachments[0].content, file_content)

        self.assertEqual(msg.attachments[0][2], mime_type)
        self.assertEqual(msg.attachments[0].mimetype, mime_type)

        attachments = self.get_decoded_attachments(msg)
        self.assertEqual(attachments[0], (file_name, file_content, mime_type))

    def test_attachments_constructor(self):
        file_name = "example.txt"
        file_content = "Text file content\n"
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
        self.assertEqual(attachments[0], (file_name, file_content, mime_type))

    def test_attachments_constructor_from_tuple(self):
        file_name = "example.txt"
        file_content = "Text file content\n"
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
        self.assertEqual(attachments[0], (file_name, file_content, mime_type))

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

    def test_decoded_attachment_text_MIMEPart(self):
        # (See also test_attach_mime_part() and test_attach_mime_part_in_constructor().)
        txt = MIMEPart()
        txt.set_content("content1")
        msg = EmailMessage(attachments=[txt])
        payload = msg.message().get_payload()
        self.assertEqual(payload[0], txt)

    def test_non_ascii_attachment_filename(self):
        """Regression test for #14964"""
        msg = EmailMessage(body="Content")
        # Unicode in file name
        msg.attach("une pièce jointe.pdf", b"%PDF-1.4.%...", mimetype="application/pdf")
        attachment = self.get_decoded_attachments(msg)[0]
        self.assertEqual(attachment.filename, "une pièce jointe.pdf")

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
                with self.subTest(
                    basename=basename, real_mimetype=real_mimetype, mimetype=mimetype
                ):
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

                    # Check attachments in the generated message.
                    # (The actual content is not checked as variations in platform
                    # line endings and rfc822 refolding complicate the logic.)
                    attachments = self.get_decoded_attachments(email)
                    self.assertEqual(len(attachments), 1)
                    actual = attachments[0]
                    self.assertEqual(actual.filename, basename)
                    self.assertEqual(actual.mimetype, expected_mimetype)

    def test_attach_text_as_bytes(self):
        """
        For text/* attachments, EmailMessage.attach() decodes bytes as UTF-8
        if possible and changes to DEFAULT_ATTACHMENT_MIME_TYPE if not.
        """
        email = EmailMessage()
        # Mimetype guessing identifies these as text/plain from the .txt extensions.
        email.attach("utf8.txt", "ütƒ-8\n".encode())
        email.attach("not-utf8.txt", b"\x86unknown-encoding\n")
        attachments = self.get_decoded_attachments(email)
        self.assertEqual(attachments[0], ("utf8.txt", "ütƒ-8\n", "text/plain"))
        self.assertEqual(
            attachments[1],
            ("not-utf8.txt", b"\x86unknown-encoding\n", "application/octet-stream"),
        )

    def test_attach_text_as_bytes_using_property(self):
        """
        The logic described in test_attach_text_as_bytes() also applies
        when directly setting the EmailMessage.attachments property.
        """
        email = EmailMessage()
        email.attachments = [
            ("utf8.txt", "ütƒ-8\n".encode(), "text/plain"),
            ("not-utf8.txt", b"\x86unknown-encoding\n", "text/plain"),
        ]
        attachments = self.get_decoded_attachments(email)
        self.assertEqual(len(attachments), 2)
        attachments = self.get_decoded_attachments(email)
        self.assertEqual(attachments[0], ("utf8.txt", "ütƒ-8\n", "text/plain"))
        self.assertEqual(
            attachments[1],
            ("not-utf8.txt", b"\x86unknown-encoding\n", "application/octet-stream"),
        )

    def test_attach_utf8_text_as_bytes(self):
        """
        Non-ASCII characters encoded as valid UTF-8 are correctly transported
        in a form that can be decoded at the receiving end.
        """
        msg = EmailMessage()
        msg.attach("file.txt", b"\xc3\xa4\n")  # UTF-8 encoded a-umlaut.
        filename, content, mimetype = self.get_decoded_attachments(msg)[0]
        self.assertEqual(filename, "file.txt")
        self.assertEqual(content, "ä\n")  # (decoded)
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

    def test_attach_8bit_rfc822_message_non_ascii(self):
        """
        Attaching a message that uses 8bit content transfer encoding for
        non-ASCII characters should not raise a UnicodeEncodeError (#36119).
        """
        attachment = dedent(
            """\
            Subject: A message using 8bit CTE
            Content-Type: text/plain; charset=utf-8
            Content-Transfer-Encoding: 8bit

            ¡8-bit content!
            """
        ).encode()
        email = EmailMessage()
        email.attach("attachment.eml", attachment, "message/rfc822")
        attachments = self.get_raw_attachments(email)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_content_type(), "message/rfc822")
        attached_message = attachments[0].get_content()
        self.assertEqual(attached_message.get_content().rstrip(), "¡8-bit content!")
        self.assertEqual(attached_message["Content-Transfer-Encoding"], "8bit")
        self.assertEqual(attached_message.get_content_type(), "text/plain")

    def test_attach_mime_part(self):
        """
        EmailMessage.attach() docs: "You can pass it
        a single argument that is a MIMEPart object."
        """
        # This also verifies complex attachments with extra header fields.
        email = EmailMessage()
        image = MIMEPart()
        image.set_content(
            b"GIF89a...",
            maintype="image",
            subtype="gif",
            disposition="inline",
            cid="<content-id@example.org>",
        )
        email.attach(image)

        attachments = self.get_raw_attachments(email)
        self.assertEqual(len(attachments), 1)
        image_att = attachments[0]
        self.assertEqual(image_att.get_content_type(), "image/gif")
        self.assertEqual(image_att.get_content_disposition(), "inline")
        self.assertEqual(image_att["Content-ID"], "<content-id@example.org>")
        self.assertEqual(image_att.get_content(), b"GIF89a...")
        self.assertIsNone(image_att.get_filename())

    def test_attach_mime_part_in_constructor(self):
        image = MIMEPart()
        image.set_content(
            b"\x89PNG...", maintype="image", subtype="png", filename="test.png"
        )
        email = EmailMessage(attachments=[image])

        attachments = self.get_raw_attachments(email)
        self.assertEqual(len(attachments), 1)
        image_att = attachments[0]
        self.assertEqual(image_att.get_content_type(), "image/png")
        self.assertEqual(image_att.get_content(), b"\x89PNG...")
        self.assertEqual(image_att.get_content_disposition(), "attachment")
        self.assertEqual(image_att.get_filename(), "test.png")

    def test_attach_rfc822_message(self):
        """
        EmailMessage.attach() docs: "If you specify a mimetype of message/rfc822,
        it will also accept django.core.mail.EmailMessage and email.message.Message."
        """
        # django.core.mail.EmailMessage
        django_email = EmailMessage("child subject", "child body")
        # email.message.Message
        py_message = PyMessage()
        py_message["Subject"] = "child subject"
        py_message.set_payload("child body")
        # email.message.EmailMessage
        py_email_message = PyEmailMessage()
        py_email_message["Subject"] = "child subject"
        py_email_message.set_content("child body")

        cases = [
            django_email,
            py_message,
            py_email_message,
            # Should also allow message serialized as str or bytes.
            py_message.as_string(),
            py_message.as_bytes(),
        ]

        for child_message in cases:
            with self.subTest(child_type=child_message.__class__):
                email = EmailMessage("parent message", "parent body")
                email.attach(content=child_message, mimetype="message/rfc822")
                self.assertEqual(len(email.attachments), 1)
                self.assertIsInstance(email.attachments[0], EmailAttachment)
                self.assertEqual(email.attachments[0].mimetype, "message/rfc822")

                # Make sure it is serialized correctly: a message/rfc822 attachment
                # whose "body" content (payload) is the "encapsulated" (child) message.
                attachments = self.get_raw_attachments(email)
                self.assertEqual(len(attachments), 1)
                rfc822_attachment = attachments[0]
                self.assertEqual(rfc822_attachment.get_content_type(), "message/rfc822")

                attached_message = rfc822_attachment.get_content()
                self.assertEqual(attached_message["Subject"], "child subject")
                self.assertEqual(attached_message.get_content().rstrip(), "child body")

                # Regression for #18967: Per RFC 2046 5.2.1, "No encoding other
                # than '7bit', '8bit', or 'binary' is permitted for the body of
                # a 'message/rfc822' entity." (Default CTE is "7bit".)
                cte = rfc822_attachment.get("Content-Transfer-Encoding", "7bit")
                self.assertIn(cte, ("7bit", "8bit", "binary"))

                # Any properly declared CTE is allowed for the attached message itself
                # (including quoted-printable or base64). For the plain ASCII content
                # in this test, we'd expect 7bit.
                child_cte = attached_message.get("Content-Transfer-Encoding", "7bit")
                self.assertEqual(child_cte, "7bit")
                self.assertEqual(attached_message.get_content_type(), "text/plain")

    def test_attach_mimepart_prohibits_other_params(self):
        email_msg = EmailMessage()
        txt = MIMEPart()
        txt.set_content("content")
        msg = (
            "content and mimetype must not be given when a MIMEPart instance "
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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_connection_arg_send_mail(self):
        mail.outbox = []
        # Send using non-default connection.
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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_connection_arg_send_mass_mail(self):
        mail.outbox = []
        # Send using non-default connection.
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

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ADMINS=["nobody@example.com"],
    )
    def test_connection_arg_mail_admins(self):
        mail.outbox = []
        # Send using non-default connection.
        connection = mail.get_connection("mail.custombackend.EmailBackend")
        mail_admins("Admin message", "Content", connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, "[Django] Admin message")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        MANAGERS=["nobody@example.com"],
    )
    def test_connection_arg_mail_managers(self):
        mail.outbox = []
        # Send using non-default connection.
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

        # Long body lines that require folding should use quoted-printable or base64,
        # whichever is shorter.
        msg = EmailMessage(
            body=(
                "Body with non latin characters: А Б В Г Д Е Ж Ѕ З И І К Л М Н О П.\n"
                "Because it has a line > 78 utf-8 octets, it should be folded, and "
                "must then be encoded using the shorter of quoted-printable or base64."
            ),
        )
        s = msg.message().as_bytes()
        self.assertIn(b"Content-Transfer-Encoding: quoted-printable", s)

    def test_address_header_handling(self):
        # This verifies the modern email API's address header handling.
        # (Adapted from older test_sanitize_address() for legacy email API.)
        cases = [
            # (address, expected_display_name, expected_addr_spec)
            ("to@example.com", "", "to@example.com"),
            # Addresses with display-names.
            ("A name <to@example.com>", "A name", "to@example.com"),
            ('"A name" <to@example.com>', "A name", "to@example.com"),
            (
                '"Comma, requires quotes" <to@example.com>',
                "Comma, requires quotes",
                "to@example.com",
            ),
            ('"to@other.com" <to@example.com>', "to@other.com", "to@example.com"),
            # Non-ASCII addr-spec: IDNA encoding for domain.
            # (Note: no RFC permits encoding a non-ASCII localpart.)
            ("to@éxample.com", "", "to@xn--xample-9ua.com"),
            (
                "To Example <to@éxample.com>",
                "To Example",
                "to@xn--xample-9ua.com",
            ),
            # Pre-encoded IDNA domain is left as is.
            # (Make sure IDNA 2008 is not downgraded to IDNA 2003.)
            ("to@xn--fa-hia.example.com", "", "to@xn--fa-hia.example.com"),
            (
                "<to@xn--10cl1a0b660p.example.com>",
                "",
                "to@xn--10cl1a0b660p.example.com",
            ),
            (
                '"Display, Name" <to@xn--nxasmm1c.example.com>',
                "Display, Name",
                "to@xn--nxasmm1c.example.com",
            ),
            # Non-ASCII display-name.
            ("Tó Example <to@example.com>", "Tó Example", "to@example.com"),
            # Addresses with two @ signs (quoted-string localpart).
            ('"to@other.com"@example.com', "", '"to@other.com"@example.com'),
            (
                'To Example <"to@other.com"@example.com>',
                "To Example",
                '"to@other.com"@example.com',
            ),
            # Addresses with long non-ASCII display names.
            (
                "Tó Example very long" * 4 + " <to@example.com>",
                "Tó Example very long" * 4,
                "to@example.com",
            ),
            # Address with long display name and non-ASCII domain.
            (
                "To Example very long" * 4 + " <to@exampl€.com>",
                "To Example very long" * 4,
                "to@xn--exampl-nc1c.com",
            ),
        ]
        for address, name, addr in cases:
            with self.subTest(address=address):
                email = EmailMessage(to=[address])
                parsed = message_from_bytes(email.message().as_bytes())
                actual = parsed["To"].addresses
                expected = (Address(display_name=name, addr_spec=addr),)
                self.assertEqual(actual, expected)

    def test_address_header_injection(self):
        msg = "Header values may not contain linefeed or carriage return characters"
        cases = [
            "Name\nInjection <to@example.com>",
            '"Name\nInjection" <to@example.com>',
            '"Name\rInjection" <to@example.com>',
            '"Name\r\nInjection" <to@example.com>',
            "Name <to\ninjection@example.com>",
            "to\ninjection@example.com",
        ]

        # Structured address header fields (from RFC 5322 3.6.x).
        headers = [
            "From",
            "Sender",
            "Reply-To",
            "To",
            "Cc",
            # "Bcc" is not checked by EmailMessage.message().
            # (See SMTPBackendTests.test_avoids_sending_to_invalid_addresses().)
            "Resent-From",
            "Resent-Sender",
            "Resent-To",
            "Resent-Cc",
            "Resent-Bcc",
        ]

        for header in headers:
            for email_address in cases:
                with self.subTest(header=header, email_address=email_address):
                    # Construct an EmailMessage with header set to email_address.
                    # Specific constructor params vary by header.
                    if header == "From":
                        email = EmailMessage(from_email=email_address)
                    elif header in ("To", "Cc", "Bcc", "Reply-To"):
                        param = header.lower().replace("-", "_")
                        email = EmailMessage(**{param: [email_address]})
                    else:
                        email = EmailMessage(headers={header: email_address})
                    with self.assertRaisesMessage(ValueError, msg):
                        email.message()

    def test_localpart_only_address(self):
        """
        Django allows sending to a localpart-only email address (without @domain).
        This is not a valid RFC 822/2822/5322 addr-spec, but is accepted by some
        SMTP servers for local delivery. Regression for #15042.
        """
        email = EmailMessage(to=["localpartonly"])
        parsed = message_from_bytes(email.message().as_bytes())
        self.assertEqual(
            parsed["To"].addresses, (Address(username="localpartonly", domain=""),)
        )

    def test_email_multi_alternatives_content_mimetype_none(self):
        email_msg = EmailMultiAlternatives()
        msg = "Both content and mimetype must be provided."
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach_alternative(None, "text/html")
        with self.assertRaisesMessage(ValueError, msg):
            email_msg.attach_alternative("<p>content</p>", None)

    def test_mime_structure(self):
        """
        Check generated messages have the expected MIME parts and nesting.
        """
        html_body = EmailAlternative("<p>HTML</p>", "text/html")
        image = EmailAttachment("image.gif", b"\x89PNG...", "image/png")
        rfc822_attachment = EmailAttachment(
            None, EmailMessage(body="text"), "message/rfc822"
        )
        cases = [
            # name, email (EmailMessage or subclass), expected structure
            (
                "single body",
                EmailMessage(body="text"),
                """
                text/plain
                """,
            ),
            (
                "single body with attachment",
                EmailMessage(body="text", attachments=[image]),
                """
                multipart/mixed
                    text/plain
                    image/png
                """,
            ),
            (
                "alternative bodies",
                EmailMultiAlternatives(body="text", alternatives=[html_body]),
                """
                multipart/alternative
                    text/plain
                    text/html
                """,
            ),
            (
                "alternative bodies with attachments",
                EmailMultiAlternatives(
                    body="text", alternatives=[html_body], attachments=[image]
                ),
                """
                multipart/mixed
                    multipart/alternative
                        text/plain
                        text/html
                    image/png
                """,
            ),
            (
                "alternative bodies with rfc822 attachment",
                EmailMultiAlternatives(
                    body="text",
                    alternatives=[html_body],
                    attachments=[rfc822_attachment],
                ),
                """
                multipart/mixed
                    multipart/alternative
                        text/plain
                        text/html
                    message/rfc822
                        text/plain
                """,
            ),
            (
                "attachment only",
                EmailMessage(attachments=[image]),
                # Avoid empty text/plain body.
                """
                multipart/mixed
                    image/png
                """,
            ),
            (
                "alternative only",
                EmailMultiAlternatives(alternatives=[html_body]),
                # Avoid empty text/plain body.
                """
                multipart/alternative
                    text/html
                """,
            ),
            (
                "alternative and attachment only",
                EmailMultiAlternatives(alternatives=[html_body], attachments=[image]),
                """
                multipart/mixed
                    multipart/alternative
                        text/html
                    image/png
                """,
            ),
            (
                "empty EmailMessage",
                EmailMessage(),
                """
                text/plain
                """,
            ),
            (
                "empty EmailMultiAlternatives",
                EmailMultiAlternatives(),
                """
                text/plain
                """,
            ),
        ]
        for name, email, expected in cases:
            expected = dedent(expected).lstrip()
            with self.subTest(name=name):
                message = email.message()
                structure = self.get_message_structure(message)
                self.assertEqual(structure, expected)

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

    def test_all_params_optional(self):
        """
        EmailMessage class docs: "All parameters are optional"
        """
        email = EmailMessage()
        self.assertIsInstance(email.message(), PyMessage)  # force serialization.

        email = EmailMultiAlternatives()
        self.assertIsInstance(email.message(), PyMessage)  # force serialization.

    def test_positional_arguments_order(self):
        """
        EmailMessage class docs: "… is initialized with the following parameters
        (in the given order, if positional arguments are used)."
        """
        connection = mail.get_connection()
        email = EmailMessage(
            # (If you need to insert/remove/reorder any params here,
            # that indicates a breaking change to documented behavior.)
            "subject",
            "body\n",
            "from@example.com",
            ["to@example.com"],
            ["bcc@example.com"],
            connection,
            [EmailAttachment("file.txt", "attachment\n", "text/plain")],
            {"X-Header": "custom header"},
            ["cc@example.com"],
            ["reply-to@example.com"],
            # (New options can be added below here, ideally as keyword-only args.)
        )

        message = email.message()
        self.assertEqual(message.get_all("Subject"), ["subject"])
        self.assertEqual(message.get_all("From"), ["from@example.com"])
        self.assertEqual(message.get_all("To"), ["to@example.com"])
        self.assertEqual(message.get_all("X-Header"), ["custom header"])
        self.assertEqual(message.get_all("Cc"), ["cc@example.com"])
        self.assertEqual(message.get_all("Reply-To"), ["reply-to@example.com"])
        self.assertEqual(message.get_payload(0).get_payload(), "body\n")
        self.assertEqual(
            self.get_decoded_attachments(email),
            [("file.txt", "attachment\n", "text/plain")],
        )
        self.assertEqual(
            email.recipients(), ["to@example.com", "cc@example.com", "bcc@example.com"]
        )
        self.assertIs(email.get_connection(), connection)

    def test_all_params_can_be_set_before_send(self):
        """
        EmailMessage class docs: "All parameters … can be set at any time
        prior to calling the send() method."
        """
        # This is meant to verify EmailMessage.__init__() doesn't apply any
        # special processing that would be missing for properties set later.
        original_connection = mail.get_connection(username="original")
        new_connection = mail.get_connection(username="new")
        email = EmailMessage(
            "original subject",
            "original body\n",
            "original-from@example.com",
            ["original-to@example.com"],
            ["original-bcc@example.com"],
            original_connection,
            [EmailAttachment("original.txt", "original attachment\n", "text/plain")],
            {"X-Header": "original header"},
            ["original-cc@example.com"],
            ["original-reply-to@example.com"],
        )
        email.subject = "new subject"
        email.body = "new body\n"
        email.from_email = "new-from@example.com"
        email.to = ["new-to@example.com"]
        email.bcc = ["new-bcc@example.com"]
        email.connection = new_connection
        image = MIMEPart()
        image.set_content(b"GIF89a...", "image", "gif")
        email.attachments = [
            ("new1.txt", "new attachment 1\n", "text/plain"),  # plain tuple
            EmailAttachment("new2.txt", "new attachment 2\n", "text/csv"),
            image,
        ]
        email.extra_headers = {"X-Header": "new header"}
        email.cc = ["new-cc@example.com"]
        email.reply_to = ["new-reply-to@example.com"]

        message = email.message()
        self.assertEqual(message.get_all("Subject"), ["new subject"])
        self.assertEqual(message.get_all("From"), ["new-from@example.com"])
        self.assertEqual(message.get_all("To"), ["new-to@example.com"])
        self.assertEqual(message.get_all("X-Header"), ["new header"])
        self.assertEqual(message.get_all("Cc"), ["new-cc@example.com"])
        self.assertEqual(message.get_all("Reply-To"), ["new-reply-to@example.com"])
        self.assertEqual(message.get_payload(0).get_payload(), "new body\n")
        self.assertEqual(
            self.get_decoded_attachments(email),
            [
                ("new1.txt", "new attachment 1\n", "text/plain"),
                ("new2.txt", "new attachment 2\n", "text/csv"),
                (None, b"GIF89a...", "image/gif"),
            ],
        )
        self.assertEqual(
            email.recipients(),
            ["new-to@example.com", "new-cc@example.com", "new-bcc@example.com"],
        )
        self.assertIs(email.get_connection(), new_connection)
        self.assertNotIn("original", message.as_string())

    def test_message_is_python_email_message(self):
        """
        EmailMessage.message() docs: "returns a Python
        email.message.EmailMessage object."
        """
        email = EmailMessage()
        message = email.message()
        self.assertIsInstance(message, PyMessage)
        self.assertEqual(message.policy, policy.default)

    def test_message_policy_smtputf8(self):
        # With SMTPUTF8, the message uses utf-8 directly in headers (not RFC 2047
        # encoded-words). Note this is the only spec-compliant way to send to
        # a non-ASCII localpart.
        email = EmailMessage(
            subject="Detta ämne innehåller icke-ASCII-tecken",
            to=["nøn-åscîi@example.com"],
        )
        message = email.message(policy=policy.SMTPUTF8)
        self.assertEqual(message.policy, policy.SMTPUTF8)
        msg_bytes = message.as_bytes()
        self.assertIn(
            "Subject: Detta ämne innehåller icke-ASCII-tecken".encode(), msg_bytes
        )
        self.assertIn("To: nøn-åscîi@example.com".encode(), msg_bytes)
        self.assertNotIn(b"=?utf-8?", msg_bytes)  # encoded-word prefix

    def test_message_policy_cte_7bit(self):
        """
        Allows a policy that requires 7bit encodings.
        """
        email = EmailMessage(body="Detta innehåller icke-ASCII-tecken")
        email.attach("file.txt", "يحتوي هذا المرفق على أحرف غير ASCII")

        # Uses 8bit by default. (Test pre-condition.)
        self.assertIn(b"Content-Transfer-Encoding: 8bit", email.message().as_bytes())

        # Uses something 7bit compatible when policy requires it. Should pick
        # the shorter of quoted-printable (for this body) or base64 (for this
        # attachment), but must not use 8bit. (Decoding to "ascii" verifies that.)
        policy_7bit = policy.default.clone(cte_type="7bit")
        msg_bytes = email.message(policy=policy_7bit).as_bytes()
        msg_ascii = msg_bytes.decode("ascii")
        self.assertIn("Content-Transfer-Encoding: quoted-printable", msg_ascii)
        self.assertIn("Content-Transfer-Encoding: base64", msg_ascii)
        self.assertNotIn("Content-Transfer-Encoding: 8bit", msg_ascii)

    def test_message_policy_compat32(self):
        """
        Although EmailMessage.message() doesn't support policy=compat32
        (because compat32 doesn't support modern APIs), compat32 _can_ be
        used with as_bytes() or as_string() on the resulting message.
        """
        # This subject results in different (but equivalent) RFC 2047 encoding
        # with compat32 vs. email.policy.default.
        email = EmailMessage(subject="Detta ämne innehåller icke-ASCII-tecken")
        message = email.message()
        self.assertIn(
            b"Subject: =?utf-8?q?Detta_=C3=A4mne_inneh=C3=A5ller_icke-ASCII-tecken?=\n",
            message.as_bytes(policy=policy.compat32),
        )
        self.assertIn(
            "Subject: =?utf-8?q?Detta_=C3=A4mne_inneh=C3=A5ller_icke-ASCII-tecken?=\n",
            message.as_string(policy=policy.compat32),
        )


@requires_tz_support
class MailTimeZoneTests(MailTestsMixin, SimpleTestCase):
    @override_settings(
        EMAIL_USE_LOCALTIME=False, USE_TZ=True, TIME_ZONE="Africa/Algiers"
    )
    def test_date_header_utc(self):
        """
        EMAIL_USE_LOCALTIME=False creates a datetime in UTC.
        """
        email = EmailMessage()
        # Per RFC 2822/5322 section 3.3, "The form '+0000' SHOULD be used
        # to indicate a time zone at Universal Time."
        self.assertEndsWith(email.message()["Date"], "+0000")

    @override_settings(
        EMAIL_USE_LOCALTIME=True, USE_TZ=True, TIME_ZONE="Africa/Algiers"
    )
    def test_date_header_localtime(self):
        """
        EMAIL_USE_LOCALTIME=True creates a datetime in the local time zone.
        """
        email = EmailMessage()
        # Africa/Algiers is UTC+1 year round.
        self.assertEndsWith(email.message()["Date"], "+0100")


class BaseEmailBackendTests(MailTestsMixin):
    email_backend = None

    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(override_settings(EMAIL_BACKEND=cls.email_backend))
        super().setUpClass()

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
            "Subject", "Content\n", "from@example.com", ["to@example.com"]
        )
        num_sent = mail.get_connection().send_messages([email])
        self.assertEqual(num_sent, 1)
        message = self.get_the_message()
        self.assertEqual(message["subject"], "Subject")
        self.assertEqual(message.get_content(), "Content\n")
        self.assertEqual(message["from"], "from@example.com")
        self.assertEqual(message.get_all("to"), ["to@example.com"])

    def test_send_unicode(self):
        email = EmailMessage(
            "Chère maman",
            "Je t'aime très fort\n",
            "from@example.com",
            ["to@example.com"],
        )
        num_sent = mail.get_connection().send_messages([email])
        self.assertEqual(num_sent, 1)
        message = self.get_the_message()
        self.assertEqual(message["subject"], "Chère maman")
        self.assertEqual(message.get_content(), "Je t'aime très fort\n")

    def test_send_long_lines(self):
        """
        Email line length is limited to 998 chars by the RFC 5322 Section 2.1.1.
        A message body containing longer lines is converted to quoted-printable
        or base64 (whichever is shorter), to avoid having to insert newlines
        in a way that alters the intended text.
        """
        cases = [
            # (body, expected_cte)
            ("В южных морях " * 60, "base64"),
            ("I de sørlige hav " * 58, "quoted-printable"),
        ]
        for body, expected_cte in cases:
            with self.subTest(body=f"{body[:10]}…", expected_cte=expected_cte):
                self.flush_mailbox()
                # Test precondition: Body is a single line < 998 characters,
                # but utf-8 encoding of body is > 998 octets (forcing a CTE
                # that avoids inserting newlines).
                self.assertLess(len(body), 998)
                self.assertGreater(len(body.encode()), 998)

                email = EmailMessage(body=body, to=["to@example.com"])
                email.send()
                message = self.get_the_message()
                self.assertMessageHasHeaders(
                    message,
                    {
                        ("MIME-Version", "1.0"),
                        ("Content-Type", 'text/plain; charset="utf-8"'),
                        ("Content-Transfer-Encoding", expected_cte),
                    },
                )

    def test_send_many(self):
        email1 = EmailMessage(to=["to-1@example.com"])
        email2 = EmailMessage(to=["to-2@example.com"])
        # send_messages() may take a list or an iterator.
        emails_lists = ([email1, email2], iter((email1, email2)))
        for emails_list in emails_lists:
            with self.subTest(emails_list=repr(emails_list)):
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
        self.assertEqual(message["from"], "Firstname Sürname <from@example.com>")

    def test_plaintext_send_mail(self):
        """
        Test send_mail without the html_message
        regression test for adding html_message parameter to send_mail()
        """
        send_mail("Subject", "Content\n", "sender@example.com", ["nobody@example.com"])
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertFalse(message.is_multipart())
        self.assertEqual(message.get_content(), "Content\n")
        self.assertEqual(message.get_content_type(), "text/plain")

    def test_html_send_mail(self):
        """Test html_message argument to send_mail"""
        send_mail(
            "Subject",
            "Content\n",
            "sender@example.com",
            ["nobody@example.com"],
            html_message="HTML Content\n",
        )
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_content(), "Content\n")
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_content(), "HTML Content\n")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")

    def test_mail_admins_and_managers(self):
        tests = (
            # The ADMINS and MANAGERS settings are lists of email strings.
            ['"Name, Full" <test@example.com>'],
            # Lists and tuples are interchangeable.
            ["test@example.com", "other@example.com"],
            ("test@example.com", "other@example.com"),
            # Lazy strings are supported.
            [gettext_lazy("test@example.com")],
        )
        for setting, mail_func in (
            ("ADMINS", mail_admins),
            ("MANAGERS", mail_managers),
        ):
            for value in tests:
                self.flush_mailbox()
                with (
                    self.subTest(setting=setting, value=value),
                    self.settings(**{setting: value}),
                ):
                    mail_func("subject", "content")
                    message = self.get_the_message()
                    expected_to = ", ".join([str(address) for address in value])
                    self.assertEqual(message.get_all("to"), [expected_to])

    @override_settings(MANAGERS=["nobody@example.com"])
    def test_html_mail_managers(self):
        """Test html_message argument to mail_managers"""
        mail_managers("Subject", "Content\n", html_message="HTML Content\n")
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "[Django] Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_content(), "Content\n")
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_content(), "HTML Content\n")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")

    @override_settings(ADMINS=["nobody@example.com"])
    def test_html_mail_admins(self):
        """Test html_message argument to mail_admins"""
        mail_admins("Subject", "Content\n", html_message="HTML Content\n")
        message = self.get_the_message()

        self.assertEqual(message.get("subject"), "[Django] Subject")
        self.assertEqual(message.get_all("to"), ["nobody@example.com"])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_content(), "Content\n")
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_content(), "HTML Content\n")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")

    @override_settings(
        ADMINS=["nobody+admin@example.com"],
        MANAGERS=["nobody+manager@example.com"],
    )
    def test_manager_and_admin_mail_prefix(self):
        """
        String prefix + lazy translated subject = bad output
        Regression for #13494
        """
        for mail_func in [mail_managers, mail_admins]:
            with self.subTest(mail_func=mail_func):
                mail_func(gettext_lazy("Subject"), "Content")
                message = self.get_the_message()
                self.assertEqual(message.get("subject"), "[Django] Subject")
                self.flush_mailbox()

    @override_settings(ADMINS=[], MANAGERS=[])
    def test_empty_admins(self):
        """
        mail_admins/mail_managers doesn't connect to the mail server
        if there are no recipients (#9383)
        """
        for mail_func in [mail_managers, mail_admins]:
            with self.subTest(mail_func=mail_func):
                mail_func("hi", "there")
                self.assertEqual(self.get_mailbox_content(), [])

    def test_wrong_admins_managers(self):
        tests = (
            "test@example.com",
            gettext_lazy("test@example.com"),
            [("nobody", "nobody@example.com"), ("other", "other@example.com")],
            [["nobody", "nobody@example.com"], ["other", "other@example.com"]],
            [("name", "test", "example.com")],
            [("Name <test@example.com",)],
            [[]],
        )
        for setting, mail_func in (
            ("ADMINS", mail_admins),
            ("MANAGERS", mail_managers),
        ):
            msg = f"The {setting} setting must be a list of email address strings."
            for value in tests:
                with (
                    self.subTest(setting=setting, value=value),
                    self.settings(**{setting: value}),
                ):
                    with self.assertRaisesMessage(ImproperlyConfigured, msg):
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
        with self.assertRaises(ValueError):
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
            message = message_from_binary_file(fp, policy=policy.default)
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
        self.smtp_envelopes = []

    async def handle_DATA(self, server, session, envelope):
        data = envelope.content
        mail_from = envelope.mail_from

        # Convert SMTP's CRNL to NL, to simplify content checks in shared test cases.
        message = message_from_bytes(data.replace(b"\r\n", b"\n"))
        try:
            header_from = message["from"].addresses[0].addr_spec
        except (KeyError, IndexError):
            header_from = None

        if mail_from != header_from:
            return f"553 '{mail_from}' != '{header_from}'"
        self.mailbox.append(message)
        self.smtp_envelopes.append(
            {
                "mail_from": envelope.mail_from,
                "rcpt_tos": envelope.rcpt_tos,
            }
        )
        return "250 OK"

    def flush_mailbox(self):
        self.mailbox[:] = []
        self.smtp_envelopes[:] = []


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

    def get_smtp_envelopes(self):
        return self.smtp_handler.smtp_envelopes

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

    def test_avoids_sending_to_invalid_addresses(self):
        """
        Verify invalid addresses can't sneak into SMTP commands through
        EmailMessage.all_recipients() (which is distinct from message header fields).
        """
        backend = smtp.EmailBackend()
        backend.connection = mock.Mock()
        for email_address in (
            # Invalid address with two @ signs.
            "to@other.com@example.com",
            # Invalid address without the quotes.
            "to@other.com <to@example.com>",
            # Multiple mailboxes in a single address.
            "to@example.com, other@example.com",
            # Other invalid addresses.
            "@",
            "to@",
            "@example.com",
            # CR/NL in addr-spec. (SMTP strips display-name.)
            '"evil@example.com\r\nto"@example.com',
            "to\nevil@example.com",
        ):
            with self.subTest(email_address=email_address):
                # Use bcc (which is only processed by SMTP backend) to ensure
                # error is coming from SMTP backend, not EmailMessage.message().
                email = EmailMessage(bcc=[email_address])
                with self.assertRaisesMessage(ValueError, "Invalid address"):
                    backend.send_messages([email])

    def test_encodes_idna_in_smtp_commands(self):
        """
        SMTP backend must encode non-ASCII domains for the SMTP envelope
        (which can be distinct from the email headers).
        """
        email = EmailMessage(
            from_email="lists@discussão.example.org",
            to=["To Example <to@漢字.example.com>"],
            bcc=["monitor@discussão.example.org"],
            headers={
                "From": "Gestor de listas <lists@discussão.example.org>",
                "To": "Discussão Django <django@discussão.example.org>",
            },
        )
        backend = smtp.EmailBackend()
        backend.send_messages([email])
        envelope = self.get_smtp_envelopes()[0]
        self.assertEqual(envelope["mail_from"], "lists@xn--discusso-xza.example.org")
        self.assertEqual(
            envelope["rcpt_tos"],
            ["to@xn--p8s937b.example.com", "monitor@xn--discusso-xza.example.org"],
        )

    def test_does_not_reencode_idna(self):
        """
        SMTP backend should not downgrade IDNA 2008 to IDNA 2003.

        Django does not currently handle IDNA 2008 encoding, but should retain
        it for addresses that have been pre-encoded.
        """
        # Test all four EmailMessage attrs accessed by the SMTP email backend.
        # These are IDNA 2008 encoded domains that would be different
        # in IDNA 2003, from https://www.unicode.org/reports/tr46/#Deviations.
        email = EmailMessage(
            from_email='"βόλος" <from@xn--fa-hia.example.com>',
            to=['"faß" <to@xn--10cl1a0b660p.example.com>'],
            cc=['"ශ්‍රී" <cc@xn--nxasmm1c.example.com>'],
            bcc=['"نامه‌ای." <bcc@xn--mgba3gch31f060k.example.com>'],
        )
        backend = smtp.EmailBackend()
        backend.send_messages([email])
        envelope = self.get_smtp_envelopes()[0]
        self.assertEqual(envelope["mail_from"], "from@xn--fa-hia.example.com")
        self.assertEqual(
            envelope["rcpt_tos"],
            [
                "to@xn--10cl1a0b660p.example.com",
                "cc@xn--nxasmm1c.example.com",
                "bcc@xn--mgba3gch31f060k.example.com",
            ],
        )

    def test_rejects_non_ascii_local_part(self):
        """
        The SMTP EmailBackend does not currently support non-ASCII local-parts.
        (That would require using the RFC 6532 SMTPUTF8 extension.) #35713.
        """
        backend = smtp.EmailBackend()
        backend.connection = mock.Mock(spec=object())
        email = EmailMessage(to=["nø@example.dk"])
        with self.assertRaisesMessage(
            ValueError,
            "Invalid address 'nø@example.dk': local-part contains non-ASCII characters",
        ):
            backend.send_messages([email])

    def test_prep_address_without_force_ascii(self):
        # A subclass implementing SMTPUTF8 could use prep_address(force_ascii=False).
        backend = smtp.EmailBackend()
        for case in ["åh@example.dk", "oh@åh.example.dk", "åh@åh.example.dk"]:
            with self.subTest(case=case):
                self.assertEqual(backend.prep_address(case, force_ascii=False), case)


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


class LegacyAPINotUsedTests(SimpleTestCase):
    """
    Check django.core.mail does not directly import Python legacy email APIs
    (other than in _deprecated.py), with a few specific exceptions.
    """

    # From "Legacy API:" in https://docs.python.org/3/library/email.html.
    legacy_email_apis = {
        "email.message.Message",
        "email.mime",
        "email.header",
        "email.charset",
        "email.encoders",
        "email.utils",
        "email.iterators",
    }

    allowed_exceptions = {
        # Compatibility in EmailMessage.attachments special cases:
        "email.message.Message",
        "email.mime.base.MIMEBase",
        # No replacement in modern email API:
        "email.utils.make_msgid",
    }

    def test_no_legacy_apis_imported(self):
        django_core_mail_path = Path(mail.__file__).parent
        django_path = django_core_mail_path.parent.parent.parent
        for abs_path in django_core_mail_path.glob("**/*.py"):
            if abs_path.name == "_deprecated.py":
                continue
            path = abs_path.relative_to(django_path)
            with self.subTest(path=str(path)):
                collector = self.ImportCollector(abs_path.read_text())
                used_apis = collector.get_matching_imports(self.legacy_email_apis)
                used_apis -= self.allowed_exceptions
                self.assertEqual(
                    "\n".join(sorted(used_apis)),
                    "",
                    f"Python legacy email APIs used in {path}",
                )

    class ImportCollector(ast.NodeVisitor):
        """
        Collect all imports from an AST as a set of fully-qualified dotted names.
        """

        def __init__(self, source=None):
            self.imports = set()
            if source:
                tree = ast.parse(source)
                self.visit(tree)

        def get_matching_imports(self, base_names):
            """
            Return the set of collected imports that start with any
            of the fully-qualified dotted names in iterable base_names.
            """
            matcher = re.compile(
                r"\b(" + r"|".join(re.escape(name) for name in base_names) + r")\b"
            )
            return set(name for name in self.imports if matcher.match(name))

        def visit_Import(self, node):
            self.imports.update(alias.name for alias in node.names)

        def visit_ImportFrom(self, node):
            self.imports.update(f"{node.module}.{alias.name}" for alias in node.names)


# Check whether python/cpython#128110 has been fixed by seeing if space
# between encoded-words is ignored (as required by RFC 2047 section 6.2).
_needs_cpython_128110_workaround = (
    _message_from_bytes(b"To: =??q?a?= =??q?b?= <to@ex>", policy=policy.default)
)["To"].addresses[0].display_name != "ab"

_rfc2047_prefix = "=?"  # start of an encoded-word.
_rfc2047_prefix_bytes = _rfc2047_prefix.encode()


def _apply_cpython_128110_workaround(message, msg_bytes):
    """
    Updates message in place to correct misparsed rfc2047 display-names
    in address headers caused by https://github.com/python/cpython/issues/128110.

    :param email.message.EmailMessage message: Message parsed with modern policy.
    :param bytes msg_bytes: Content from which message was parsed.
    """
    from email.header import decode_header
    from email.headerregistry import AddressHeader
    from email.parser import BytesHeaderParser
    from email.utils import getaddresses

    def rfc2047_decode(s):
        # Decode using legacy decode_header() (which doesn't have the bug).
        return "".join(
            (
                segment
                if charset is None and isinstance(segment, str)
                else segment.decode(charset or "ascii")
            )
            for segment, charset in decode_header(s)
        )

    def build_address(name, address):
        if "@" in address:
            return Address(display_name=name, addr_spec=address)
        else:
            return Address(display_name=name, username=address, domain="")

    # This workaround only applies to messages parsed with a modern policy.
    assert not isinstance(message.policy, policy.Compat32)

    # Reparse with compat32 to get access to raw (undecoded) headers.
    raw_headers = BytesHeaderParser(policy=policy.compat32).parsebytes(msg_bytes)
    for header, modern_value in message.items():
        if not isinstance(modern_value, AddressHeader):
            # The bug only affects structured address headers.
            continue
        raw_value = raw_headers[header]
        if _rfc2047_prefix in raw_value:
            # This workaround doesn't handle headers that appear more than once.
            assert len(message.get_all(header)) == 1
            # Reconstruct Address objects using legacy APIs (which don't have the bug).
            unfolded = raw_value.replace("\r\n", "").replace("\n", "")
            corrected_addresses = (
                build_address(rfc2047_decode(name), address)
                for name, address in getaddresses([unfolded])
            )
            message.replace_header(header, corrected_addresses)
