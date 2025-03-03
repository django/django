# RemovedInDjango70Warning: this entire file
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from unittest import mock

from django.core.mail import (
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
)
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango70Warning

from .tests import MailTestsMixin


class DeprecationWarningTests(MailTestsMixin, SimpleTestCase):
    def test_attach_mime_image(self):
        """
        EmailMessage.attach() docs: "You can pass it
        a single argument that is a MIMEBase instance."
        """
        msg = (
            "MIMEBase attachments are deprecated."
            " Use an email.message.MIMEPart instead."
        )
        # This also verifies complex attachments with extra header fields.
        email = EmailMessage()
        image = MIMEImage(b"GIF89a...", "gif")
        image["Content-Disposition"] = "inline"
        image["Content-ID"] = "<content-id@example.org>"
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            email.attach(image)

        attachments = self.get_raw_attachments(email)
        self.assertEqual(len(attachments), 1)
        image_att = attachments[0]
        self.assertEqual(image_att.get_content_type(), "image/gif")
        self.assertEqual(image_att.get_content_disposition(), "inline")
        self.assertEqual(image_att["Content-ID"], "<content-id@example.org>")
        self.assertEqual(image_att.get_content(), b"GIF89a...")
        self.assertIsNone(image_att.get_filename())

    def test_attach_mime_image_in_constructor(self):
        msg = (
            "MIMEBase attachments are deprecated."
            " Use an email.message.MIMEPart instead."
        )
        image = MIMEImage(b"\x89PNG...", "png")
        image["Content-Disposition"] = "attachment; filename=test.png"
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            email = EmailMessage(attachments=[image])

        attachments = self.get_raw_attachments(email)
        self.assertEqual(len(attachments), 1)
        image_att = attachments[0]
        self.assertEqual(image_att.get_content_type(), "image/png")
        self.assertEqual(image_att.get_content(), b"\x89PNG...")
        self.assertEqual(image_att.get_filename(), "test.png")

    def test_deprecated_on_import(self):
        """
        These items are not typically called from user code,
        so generate deprecation warnings immediately at the time
        they are imported from django.core.mail.
        """
        cases = [
            # name, msg
            (
                "BadHeaderError",
                "BadHeaderError is deprecated. Replace with ValueError.",
            ),
            (
                "SafeMIMEText",
                "SafeMIMEText is deprecated. The return value of"
                " EmailMessage.message() is an email.message.EmailMessage.",
            ),
            (
                "SafeMIMEMultipart",
                "SafeMIMEMultipart is deprecated. The return value of"
                " EmailMessage.message() is an email.message.EmailMessage.",
            ),
            (
                "forbid_multi_line_headers",
                "The internal API forbid_multi_line_headers() is deprecated.",
            ),
        ]
        for name, msg in cases:
            with self.subTest(name=name):
                with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
                    __import__("django.core.mail", fromlist=[name])

    def test_sanitize_address_deprecated(self):
        from django.core.mail.message import sanitize_address

        msg = "The internal API sanitize_address() is deprecated."
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            sanitize_address("to@example.com", "ascii")

    def test_forbid_multi_line_headers_deprecated(self):
        # Import from _deprecated to avoid warning on import.
        # This function also warns (with a more detailed message) on use.
        from django.core.mail._deprecated import forbid_multi_line_headers

        msg = "The internal API forbid_multi_line_headers() is deprecated."
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            forbid_multi_line_headers("To", "to@example.com", "ascii")


class UndocumentedFeatureErrorTests(SimpleTestCase):
    """
    These undocumented features were removed without going through deprecation.
    In case they were being used, they now raise errors.
    """

    def test_undocumented_mixed_subtype(self):
        """
        Trying to use the previously undocumented, now unsupported
        EmailMessage.mixed_subtype causes an error.
        """
        msg = (
            "EmailMessage no longer supports"
            " the undocumented `mixed_subtype` attribute"
        )
        email = EmailMessage(
            attachments=[EmailAttachment(None, b"GIF89a...", "image/gif")]
        )
        email.mixed_subtype = "related"
        with self.assertRaisesMessage(AttributeError, msg):
            email.message()

    def test_undocumented_alternative_subtype(self):
        """
        Trying to use the previously undocumented, now unsupported
        EmailMultiAlternatives.alternative_subtype causes an error.
        """
        msg = (
            "EmailMultiAlternatives no longer supports"
            " the undocumented `alternative_subtype` attribute"
        )
        email = EmailMultiAlternatives(
            alternatives=[EmailAlternative("", "text/plain")]
        )
        email.alternative_subtype = "multilingual"
        with self.assertRaisesMessage(AttributeError, msg):
            email.message()


@ignore_warnings(category=RemovedInDjango70Warning)
class DeprecatedCompatibilityTests(SimpleTestCase):
    def test_bad_header_error(self):
        """
        Existing code that catches deprecated BadHeaderError should be
        compatible with modern email (which raises ValueError instead).
        """
        from django.core.mail import BadHeaderError

        with self.assertRaises(BadHeaderError):
            EmailMessage(subject="Bad\r\nHeader").message()

    def test_attachments_mimebase_in_constructor(self):
        txt = MIMEText("content1")
        msg = EmailMessage(attachments=[txt])
        payload = msg.message().get_payload()
        self.assertEqual(payload[0], txt)


@ignore_warnings(category=RemovedInDjango70Warning)
class DeprecatedFeatureTests(SimpleTestCase):
    """
    Original test cases for the deprecated email features.
    """

    @mock.patch("django.core.mail._deprecated.MIMEText.set_payload")
    def test_nonascii_as_string_with_ascii_charset(self, mock_set_payload):
        """Line length check should encode the payload supporting `surrogateescape`.

        Following https://github.com/python/cpython/issues/76511, newer
        versions of Python (3.12.3 and 3.13) ensure that a message's
        payload is encoded with the provided charset and `surrogateescape` is
        used as the error handling strategy.

        This test is heavily based on the test from the fix for the bug above.
        Line length checks in SafeMIMEText's set_payload should also use the
        same error handling strategy to avoid errors such as:

        UnicodeEncodeError: 'utf-8' codec can't encode <...>: surrogates not allowed
        """
        from django.core.mail import SafeMIMEText

        def simplified_set_payload(instance, payload, charset):
            instance._payload = payload

        mock_set_payload.side_effect = simplified_set_payload

        text = (
            "Text heavily based in Python's text for non-ascii messages: Föö bär"
        ).encode("iso-8859-1")
        body = text.decode("ascii", errors="surrogateescape")
        message = SafeMIMEText(body, "plain", "ascii")
        mock_set_payload.assert_called_once()
        self.assertEqual(message.get_payload(decode=True), text)

    def test_sanitize_address(self):
        """Email addresses are properly sanitized."""
        from django.core.mail.message import sanitize_address

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
            # But an 'encoded-word' localpart is prohibited by RFC-2047, and not
            # supported by any known mail service. This incorrect behavior
            # is preserved in sanitize_address() for compatibility.
            ("tó@example.com", "utf-8", "=?utf-8?b?dMOz?=@example.com"),
            ("to@éxample.com", "utf-8", "to@xn--xample-9ua.com"),
            (
                ("Tó Example", "tó@example.com"),
                "utf-8",
                # (Not RFC-2047 compliant.)
                "=?utf-8?q?T=C3=B3_Example?= <=?utf-8?b?dMOz?=@example.com>",
            ),
            # Unicode addresses with display names.
            (
                "Tó Example <tó@example.com>",
                "utf-8",
                # (Not RFC-2047 compliant.)
                "=?utf-8?q?T=C3=B3_Example?= <=?utf-8?b?dMOz?=@example.com>",
            ),
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
        from django.core.mail.message import sanitize_address

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
        from django.core.mail.message import sanitize_address

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


class PythonGlobalState(SimpleTestCase):
    """
    Tests for #12422 -- Django smarts (#2472/#11212) with charset of utf-8 text
    parts shouldn't pollute global email Python package charset registry when
    django.mail.message is imported.
    """

    @classmethod
    def setUpClass(cls):
        # Make sure code that creates custom email charsets has been run.
        from django.core.mail._deprecated import (  # NOQA: F401
            utf8_charset,
            utf8_charset_qp,
        )

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
