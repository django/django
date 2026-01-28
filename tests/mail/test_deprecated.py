# RemovedInDjango70Warning: This entire file.
from email.mime.text import MIMEText

from django.core.mail import (
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
)
from django.core.mail.message import forbid_multi_line_headers, sanitize_address
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango70Warning

from .tests import MailTestsMixin


class DeprecationWarningTests(MailTestsMixin, SimpleTestCase):
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
        ]
        for name, msg in cases:
            with self.subTest(name=name):
                with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
                    __import__("django.core.mail", fromlist=[name])

    def test_sanitize_address_deprecated(self):
        msg = (
            "The internal API sanitize_address() is deprecated."
            " Python's modern email API (with email.message.EmailMessage or"
            " email.policy.default) will handle most required validation and"
            " encoding. Use Python's email.headerregistry.Address to construct"
            " formatted addresses from component parts."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            sanitize_address("to@example.com", "ascii")

    def test_forbid_multi_line_headers_deprecated(self):
        msg = (
            "The internal API forbid_multi_line_headers() is deprecated."
            " Python's modern email API (with email.message.EmailMessage or"
            " email.policy.default) will reject multi-line headers."
        )
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
