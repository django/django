import os
import shutil
import socket
import sys
import tempfile
from io import StringIO
from pathlib import Path
from smtplib import SMTPException
from ssl import SSLError
from unittest import mock, skipUnless

from django.core import mail
from django.core.mail import EmailMessage
from django.core.mail.backends import dummy, locmem, smtp
from django.test import SimpleTestCase, override_settings

from .tests import MailTestsMixin, message_from_bytes

try:
    from aiosmtpd.controller import Controller

    HAS_AIOSMTPD = True
except ImportError:
    HAS_AIOSMTPD = False


class SharedEmailBackendTests(MailTestsMixin):
    """Common test cases run against each EmailBackend."""

    email_backend = None

    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(override_settings(EMAIL_BACKEND=cls.email_backend))
        super().setUpClass()

    def get_mailbox_content(self):
        raise NotImplementedError(
            "Subclasses of SharedEmailBackendTests must provide a "
            "get_mailbox_content() method."
        )

    def flush_mailbox(self):
        raise NotImplementedError(
            "Subclasses of SharedEmailBackendTests may require a "
            "flush_mailbox() method."
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

    def test_connection_can_be_closed_even_if_not_opened(self):
        backend = mail.get_connection()
        backend.close()

    def test_connection_can_be_used_as_contextmanager(self):
        backend = mail.get_connection()
        backend.open = mock.Mock()
        backend.close = mock.Mock()

        with backend as backend_cm:
            backend.open.assert_called_once()
            self.assertIs(backend_cm, backend)
            backend.close.assert_not_called()

        backend.close.assert_called_once()


class DummyBackendTests(SharedEmailBackendTests, SimpleTestCase):
    email_backend = "django.core.mail.backends.dummy.EmailBackend"

    def get_mailbox_content(self):
        # Shared tests that examine the content of sent messages are not
        # meaningful: the dummy backend immediately discards sent messages,
        # so it's not possible to retrieve them.
        self.skipTest("Dummy backend discards sent messages")

    def flush_mailbox(self):
        pass

    def test_send_messages_returns_sent_count(self):
        backend = dummy.EmailBackend()
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(backend.send_messages([email, email, email]), 3)


class LocmemBackendTests(SharedEmailBackendTests, SimpleTestCase):
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
        Make sure that the locmem backend populates the outbox.
        """
        backend1 = locmem.EmailBackend()
        backend2 = locmem.EmailBackend()
        email = EmailMessage(to=["to@example.com"])
        backend1.send_messages([email])
        backend2.send_messages([email])
        self.assertEqual(len(mail.outbox), 2)

    def test_validate_multiline_headers(self):
        # Headers are validated when using the locmem backend (#18861).
        # (See also EmailMessageTests.test_header_injection().)
        email = EmailMessage(subject="Subject\nMultiline", to=["to@example.com"])
        backend = locmem.EmailBackend()
        with self.assertRaises(ValueError):
            backend.send_messages([email])

    def test_outbox_not_mutated_after_send(self):
        email = EmailMessage(
            subject="correct subject",
            to=["to@example.com"],
        )
        backend = locmem.EmailBackend()
        backend.send_messages([email])
        email.subject = "other subject"
        email.to.append("other@example.com")
        self.assertEqual(mail.outbox[0].subject, "correct subject")
        self.assertEqual(mail.outbox[0].to, ["to@example.com"])


class FileBackendTests(SharedEmailBackendTests, SimpleTestCase):
    email_backend = "django.core.mail.backends.filebased.EmailBackend"

    def setUp(self):
        super().setUp()
        self.tmp_dir = self.mkdtemp()
        _settings_override = override_settings(EMAIL_FILE_PATH=self.tmp_dir)
        _settings_override.enable()
        self.addCleanup(_settings_override.disable)

    def mkdtemp(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        return tmp_dir

    def get_filenames(self):
        return os.listdir(self.tmp_dir)

    def get_messages_from_filename(self, filename):
        with open(os.path.join(self.tmp_dir, filename), "rb") as fp:
            messages = fp.read().split(b"\n" + (b"-" * 79) + b"\n")
            return [message_from_bytes(m) for m in messages if m]

    def flush_mailbox(self):
        for filename in self.get_filenames():
            os.unlink(os.path.join(self.tmp_dir, filename))

    def get_mailbox_content(self):
        messages = []
        for filename in self.get_filenames():
            messages.extend(self.get_messages_from_filename(filename))
        return messages

    def test_new_file_per_instance(self):
        # Documented behavior: "A new file is created for each new session that
        # is opened on this backend."
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(len(self.get_filenames()), 0)

        backend1 = mail.get_connection()
        backend1.send_messages([email])
        self.assertEqual(len(self.get_filenames()), 1)

        backend2 = mail.get_connection()
        backend2.send_messages([email])
        self.assertEqual(len(self.get_filenames()), 2)

    def test_multiple_messages_same_connection_single_file_reused(self):
        self.assertEqual(len(self.get_filenames()), 0)
        backend = mail.get_connection()

        self.assertIs(backend.open(), True)
        backend.send_messages([EmailMessage(to=["one@example.com"])])
        filenames = self.get_filenames()
        self.assertEqual(len(filenames), 1)

        # Send a second message while connection is still open.
        backend.send_messages([EmailMessage(to=["two@example.com"])])
        self.assertEqual(self.get_filenames(), filenames)

        backend.close()
        self.assertEqual(self.get_filenames(), filenames)

        messages = self.get_messages_from_filename(filenames[0])
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["to"], "one@example.com")
        self.assertEqual(messages[1]["to"], "two@example.com")

    def test_reopening_connection_uses_same_file(self):
        self.assertEqual(len(self.get_filenames()), 0)

        backend = mail.get_connection()
        self.assertIs(backend.open(), True)
        backend.send_messages([EmailMessage(to=["one@example.com"])])
        backend.close()
        filenames = self.get_filenames()
        self.assertEqual(len(filenames), 1)

        # Reopen the connection.
        self.assertIs(backend.open(), True)
        backend.send_messages([EmailMessage(to=["two@example.com"])])
        self.assertEqual(self.get_filenames(), filenames)
        backend.close()
        self.assertEqual(self.get_filenames(), filenames)

        messages = self.get_messages_from_filename(filenames[0])
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["to"], "one@example.com")
        self.assertEqual(messages[1]["to"], "two@example.com")


class FileBackendPathLibTests(FileBackendTests):
    """Repeat FileBackendTests cases using a Path object as file_path."""

    def mkdtemp(self):
        tmp_dir = super().mkdtemp()
        return Path(tmp_dir)


class ConsoleBackendTests(SharedEmailBackendTests, SimpleTestCase):
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
        s = StringIO()
        backend = mail.get_connection(
            "django.core.mail.backends.console.EmailBackend", stream=s
        )
        backend.send_messages([EmailMessage(to=["to@example.com"])])
        message = s.getvalue().split("\n" + ("-" * 79) + "\n")[0].encode()
        self.assertMessageHasHeaders(
            message,
            {("To", "to@example.com")},
        )
        self.assertIn(b"\nDate: ", message)


class SMTPHandler:
    def __init__(self, *args, **kwargs):
        self.mailbox = []
        self.smtp_envelopes = []

    async def handle_DATA(self, server, session, envelope):
        data = envelope.content
        mail_from = envelope.mail_from

        # Convert SMTP's CRNL to NL, to simplify content checks in shared test
        # cases.
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
class SMTPBackendTests(SharedEmailBackendTests, SMTPBackendTestsBase):
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
        with mock.patch("smtplib.SMTP.login") as mock_smtp_login, backend:
            # Using backend as context manager opens the connection and
            # attempts login.
            pass
        mock_smtp_login.assert_called_once_with(
            "not empty username", "not empty password"
        )

    def test_server_open(self):
        """
        open() returns whether it opened a connection.
        """
        backend = smtp.EmailBackend()
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
        self.assertIs(backend.use_tls, True)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_override_settings(self):
        backend = smtp.EmailBackend(use_tls=False)
        self.assertIs(backend.use_tls, False)

    def test_email_tls_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertIs(backend.use_tls, False)

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
        self.assertIs(backend.use_ssl, True)

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_override_settings(self):
        backend = smtp.EmailBackend(use_ssl=False)
        self.assertIs(backend.use_ssl, False)

    def test_email_ssl_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertIs(backend.use_ssl, False)

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
        self.assertIs(backend.use_tls, True)
        with self.assertRaisesMessage(
            SMTPException, "STARTTLS extension not supported by server."
        ):
            with backend:
                pass

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_attempts_ssl_connection(self):
        backend = smtp.EmailBackend()
        self.assertIs(backend.use_ssl, True)
        with self.assertRaises(SSLError):
            with backend:
                pass

    def test_connection_timeout_default(self):
        backend = mail.get_connection("django.core.mail.backends.smtp.EmailBackend")
        self.assertIsNone(backend.timeout)

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
    def test_email_timeout_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.timeout, 10)

    def test_serialized_message_uses_crlf_line_ending(self):
        backend = mail.get_connection()
        with (
            backend,
            mock.patch.object(backend.connection, "sendmail") as mock_sendmail,
        ):
            backend.send_messages([EmailMessage(to=["to@example.com"])])

        # The third argument to SMTP.sendmail() is the serialized message.
        mock_sendmail.assert_called_once()
        msg = mock_sendmail.call_args.args[2].decode()
        # The message only contains CRLF and not combinations of CRLF, LF, and
        # CR (#23063).
        msg = msg.replace("\r\n", "")
        self.assertNotIn("\r", msg)
        self.assertNotIn("\n", msg)

    def test_send_messages_after_open_failed(self):
        """
        send_messages() shouldn't try to send messages if open() raises an
        exception after initializing the connection.
        """
        backend = smtp.EmailBackend()
        # Simulate connection initialization success and a subsequent
        # connection exception.
        backend.connection = mock.Mock()
        backend.open = lambda: None
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(backend.send_messages([email]), 0)

    def test_send_messages_with_empty_list_does_not_open_connection(self):
        backend = smtp.EmailBackend()
        backend.open = mock.Mock()
        self.assertEqual(backend.send_messages([]), 0)
        backend.open.assert_not_called()

    def test_send_messages_zero_sent(self):
        """A message isn't sent if it doesn't have any recipients."""
        backend = smtp.EmailBackend()
        backend.connection = mock.Mock()
        email = EmailMessage("Subject", "Content", "from@example.com", to=[])
        sent = backend.send_messages([email])
        self.assertEqual(sent, 0)
        backend.connection.sendmail.assert_not_called()

    def test_avoids_sending_to_invalid_addresses(self):
        """
        Verify invalid addresses can't sneak into SMTP commands through
        EmailMessage.all_recipients() (which is distinct from message header
        fields).
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
                # error is coming from SMTP backend, not
                # EmailMessage.message().
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
        # A subclass implementing SMTPUTF8 could use
        # prep_address(force_ascii=False).
        backend = smtp.EmailBackend()
        for case in ["åh@example.dk", "oh@åh.example.dk", "åh@åh.example.dk"]:
            with self.subTest(case=case):
                self.assertEqual(backend.prep_address(case, force_ascii=False), case)


@skipUnless(HAS_AIOSMTPD, "No aiosmtpd library detected.")
class SMTPBackendStoppedServerTests(SMTPBackendTestsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = smtp.EmailBackend()
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
