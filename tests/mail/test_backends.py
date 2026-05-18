import os
import re
import shutil
import socket
import ssl
import sys
import tempfile
from email.errors import HeaderWriteError
from email.message import EmailMessage as PyEmailMessage
from io import StringIO
from pathlib import Path
from smtplib import SMTPException
from ssl import SSLError
from unittest import mock, skipIf, skipUnless

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, InvalidMailer
from django.core.mail.backends import console, dummy, filebased, locmem, smtp
from django.core.mail.backends.base import BaseEmailBackend
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango70Warning

from .tests import MailTestsMixin, message_from_bytes

try:
    from aiosmtpd.controller import Controller

    HAS_AIOSMTPD = True
except ImportError:
    HAS_AIOSMTPD = False


class BaseEmailBackendTests(SimpleTestCase):
    def test_alias_arg_accepted(self):
        backend = BaseEmailBackend(alias="test_alias")
        self.assertEqual(backend.alias, "test_alias")

    # RemovedInDjango70Warning.
    def test_fail_silently_arg_accepted(self):
        msg_init = "BaseEmailBackend.__init__() does not support 'fail_silently'."
        msg_use = "BaseEmailBackend.fail_silently is deprecated."
        for value in [True, False]:
            with self.subTest(fail_silently=value):
                with self.assertWarnsMessage(RemovedInDjango70Warning, msg_init):
                    backend = BaseEmailBackend(fail_silently=value)
                with self.assertWarnsMessage(RemovedInDjango70Warning, msg_use):
                    self.assertIs(backend.fail_silently, value)

    def test_unknown_kwargs_error(self):
        msg = "MAILERS['test_alias']: Unknown options 'oops_typo', 'unknown'."
        with self.assertRaisesMessage(InvalidMailer, msg):
            BaseEmailBackend(alias="test_alias", oops_typo="foo", unknown="bar")

    # RemovedInDjango70Warning.
    def test_unknown_kwargs_ignored(self):
        # In compatibility mode (without alias), unknown keyword args are
        # ignored with a deprecation warning.
        msg = (
            "BaseEmailBackend.__init__() does not support 'oops_typo', "
            "'unknown'. In Django 7.0, BaseEmailBackend will raise a "
            "TypeError for unknown keyword arguments."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            backend = BaseEmailBackend(oops_typo="foo", unknown="foo")
            self.assertIsInstance(backend, BaseEmailBackend)
            self.assertFalse(hasattr(backend, "oops_typo"))
            self.assertFalse(hasattr(backend, "unknown"))


class SharedEmailBackendTests(MailTestsMixin):
    """Common test cases run against each EmailBackend."""

    # Subclasses must set to the EmailBackend class being tested.
    backend_class = None

    # Create an instance of the backend_class for use in this test context
    # (configured for use with get_mailbox_content() and flush_mailbox()).
    # Subclasses should override to default kwargs for testing if needed.
    def create_backend(self, *, alias="test_alias", **kwargs):
        if self.backend_class is None:
            raise NotImplementedError(
                "Subclasses of SharedEmailBackendTests must provide a "
                "backend_class attribute."
            )
        if alias is not None:
            kwargs["alias"] = alias
        return self.backend_class(**kwargs)

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

    def test_accepts_alias(self):
        backend = self.create_backend(alias="this-alias")
        self.assertEqual(backend.alias, "this-alias")

    # RemovedInDjango70Warning.
    def test_alias_is_optional_during_transition_to_mailers(self):
        # alias=None tells create_backend() to _omit_ the `alias` arg.
        backend = self.create_backend(alias=None)
        self.assertIsNone(backend.alias)

    def test_create_from_mailers(self, required_options=None):
        # Subclasses must override this test case if any options are required.
        backend_import_path = (
            f"{self.backend_class.__module__}.{self.backend_class.__name__}"
        )
        with self.settings(
            MAILERS={
                "custom": {
                    "BACKEND": backend_import_path,
                    "OPTIONS": required_options or {},
                }
            }
        ):
            backend = mail.mailers["custom"]
            self.assertIsInstance(backend, self.backend_class)
            self.assertEqual(backend.alias, "custom")

    def test_send(self):
        email = EmailMessage(
            "Subject", "Content\n", "from@example.com", ["to@example.com"]
        )
        num_sent = self.create_backend().send_messages([email])
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
        num_sent = self.create_backend().send_messages([email])
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
                num_sent = self.create_backend().send_messages(emails_list)
                self.assertEqual(num_sent, 2)
                messages = self.get_mailbox_content()
                self.assertEqual(len(messages), 2)
                self.assertEqual(messages[0]["To"], "to-1@example.com")
                self.assertEqual(messages[1]["To"], "to-2@example.com")
                self.flush_mailbox()

    def test_connection_can_be_closed_even_if_not_opened(self):
        backend = self.create_backend()
        backend.close()

    def test_connection_can_be_used_as_contextmanager(self):
        backend = self.create_backend()
        backend.open = mock.Mock()
        backend.close = mock.Mock()

        with backend as backend_cm:
            backend.open.assert_called_once()
            self.assertIs(backend_cm, backend)
            backend.close.assert_not_called()

        backend.close.assert_called_once()

    # RemovedInDjango70Warning. (But keep overrides in subclasses.)
    def test_fail_silently_arg_accepted(self):
        # In Django 7.0, the fail_silently arg will *not* be accepted by
        # BaseEmailBackend. Backends that *do* support fail_silently must
        # handle that argument themselves. Tests for those backends should
        # override this test case to reflect continuing fail_silently support.
        with self.subTest("Compatibility configuration"):
            # Backend initialized in compatibility mode (without alias) warns
            # but still sets attribute. (alias=None tells create_backend to
            # _omit_ the `alias` arg.)
            msg_init = "EmailBackend.__init__() does not support 'fail_silently'."
            msg_use = "EmailBackend.fail_silently is deprecated."
            for value in [True, False]:
                with self.subTest(fail_silently=value):
                    with self.assertWarnsMessage(RemovedInDjango70Warning, msg_init):
                        backend = self.create_backend(alias=None, fail_silently=value)
                    with self.assertWarnsMessage(RemovedInDjango70Warning, msg_use):
                        self.assertIs(backend.fail_silently, value)

        with self.subTest("Updated configuration"):
            # Backend initialized with alias raises error.
            msg_init = "MAILERS['test_alias']: Unknown options 'fail_silently'."
            with self.assertRaisesMessage(InvalidMailer, msg_init):
                self.create_backend(fail_silently=True)

    def test_unknown_kwargs_error(self):
        msg = "MAILERS['test_alias']: Unknown options 'oops_typo', 'unknown'."
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(oops_typo=True, unknown="foo")

    # RemovedInDjango70Warning.
    def test_unknown_kwargs_ignored(self):
        # In compatibility mode (without alias), unknown keyword args are
        # ignored with a deprecation warning.
        backend_module = self.backend_class.__module__
        msg = (
            f"{backend_module}.EmailBackend.__init__() does not support "
            "'unknown_kwarg'. In Django 7.0, BaseEmailBackend will raise a "
            "TypeError for unknown keyword arguments."
        )
        with (
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ignore_warnings(
                category=RemovedInDjango70Warning,
                message=re.escape(
                    "Directly creating EmailBackend instances is deprecated."
                ),
            ),
        ):
            # alias=None tells create_backend() to _omit_ the `alias` arg.
            backend = self.create_backend(alias=None, unknown_kwarg="foo")
            self.assertFalse(hasattr(backend, "unknown_kwarg"))


class DummyBackendTests(SharedEmailBackendTests, SimpleTestCase):
    backend_class = dummy.EmailBackend

    def get_mailbox_content(self):
        # Shared tests that examine the content of sent messages are not
        # meaningful: the dummy backend immediately discards sent messages,
        # so it's not possible to retrieve them.
        self.skipTest("Dummy backend discards sent messages")

    def flush_mailbox(self):
        pass

    def test_send_messages_returns_sent_count(self):
        backend = self.create_backend()
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(backend.send_messages([email, email, email]), 3)


class LocmemBackendTests(SharedEmailBackendTests, SimpleTestCase):
    backend_class = locmem.EmailBackend

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
        backend1 = self.create_backend()
        backend2 = self.create_backend()
        email = EmailMessage(to=["to@example.com"])
        backend1.send_messages([email])
        backend2.send_messages([email])
        self.assertEqual(len(mail.outbox), 2)

    def test_validate_multiline_headers(self):
        # Headers are validated when using the locmem backend (#18861).
        # (See also EmailMessageTests.test_header_injection().)
        email = EmailMessage(subject="Subject\nMultiline", to=["to@example.com"])
        backend = self.create_backend()
        with self.assertRaises(ValueError):
            backend.send_messages([email])

    def test_outbox_not_mutated_after_send(self):
        email = EmailMessage(
            subject="correct subject",
            to=["to@example.com"],
        )
        backend = self.create_backend()
        backend.send_messages([email])
        email.subject = "other subject"
        email.to.append("other@example.com")
        self.assertEqual(mail.outbox[0].subject, "correct subject")
        self.assertEqual(mail.outbox[0].to, ["to@example.com"])

    def test_adds_sent_using_attribute(self):
        email = EmailMessage("to@example.com")
        locmem.EmailBackend(alias="custom").send_messages([email])
        locmem.EmailBackend().send_messages([email])

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].sent_using, "custom")
        self.assertIsNone(mail.outbox[1].sent_using)


@ignore_warnings(
    category=RemovedInDjango70Warning,
    message=r"The EMAIL_FILE_PATH setting is deprecated\.",
)
class FileBackendTests(SharedEmailBackendTests, SimpleTestCase):
    backend_class = filebased.EmailBackend

    def setUp(self):
        super().setUp()
        self.tmp_dir = self.mkdtemp()

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

    def create_backend(self, **kwargs):
        kwargs.setdefault("file_path", self.tmp_dir)
        return super().create_backend(**kwargs)

    def flush_mailbox(self):
        for filename in self.get_filenames():
            os.unlink(os.path.join(self.tmp_dir, filename))

    def get_mailbox_content(self):
        messages = []
        for filename in self.get_filenames():
            messages.extend(self.get_messages_from_filename(filename))
        return messages

    def test_fail_silently_arg_accepted(self):
        # RemovedInDjango70Warning: remove this comment (but keep the test).
        # The file backend continues to support fail_silently. Override the
        # SharedEmailBackendTests case that treats it as deprecated.
        for value in [True, False]:
            with self.subTest(fail_silently=value):
                backend = self.create_backend(fail_silently=value)
                self.assertIs(backend.fail_silently, value)

    def test_create_from_mailers(self):
        super().test_create_from_mailers(required_options={"file_path": self.tmp_dir})

    # RemovedInDjango70Warning.
    def test_email_file_path_use_settings(self):
        file_path_settings = self.mkdtemp()
        with self.settings(EMAIL_FILE_PATH=file_path_settings):
            backend = filebased.EmailBackend()
        self.assertEqual(backend.file_path, str(file_path_settings))

    # RemovedInDjango70Warning.
    def test_email_file_path_override_settings(self):
        file_path_settings = self.mkdtemp()
        file_path_override = self.mkdtemp()
        self.assertNotEqual(file_path_settings, file_path_override)

        with self.settings(EMAIL_FILE_PATH=file_path_settings):
            backend = filebased.EmailBackend(file_path=file_path_override)
        self.assertEqual(backend.file_path, str(file_path_override))

    # RemovedInDjango70Warning.
    def test_error_if_email_file_path_setting_not_defined(self):
        msg = "The EMAIL_FILE_PATH setting must be set to use the file EmailBackend."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            filebased.EmailBackend()

    def test_file_path_option_required(self):
        msg = "MAILERS['test_alias']: OPTIONS must define 'file_path'."
        with self.assertRaisesMessage(InvalidMailer, msg):
            filebased.EmailBackend(alias="test_alias")

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_FILE_PATH="/this/path/does/not/exist")
    def test_ignores_settings_when_initialized_with_alias(self):
        backend = self.create_backend()
        self.assertEqual(backend.file_path, str(self.tmp_dir))

    def test_error_if_file_path_is_not_directory(self):
        tmp_file = Path(self.tmp_dir) / "ordinary-file"
        tmp_file.touch()
        if isinstance(self.tmp_dir, str):
            # Running the non-"PathLib" version of FileBackendTests.
            tmp_file = str(tmp_file)
        msg = f"MAILERS['test_alias']: 'file_path' is not a directory: {tmp_file}"
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(file_path=tmp_file)

        # RemovedInDjango70Warning.
        with self.subTest("Compatibility"):
            msg = (
                "Path for saving email messages exists, but is not a "
                f"directory: {tmp_file}"
            )
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                # alias=None tells create_backend() to _omit_ the `alias` arg.
                self.create_backend(alias=None, file_path=tmp_file)

    @skipIf(
        sys.platform == "win32",
        "No cross-platform means to force an OSError from os.makedirs().",
    )
    def test_error_if_file_path_cannot_be_created(self):
        msg = "MAILERS['test_alias']: Could not create 'file_path': /dev/null/foo"
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(file_path="/dev/null/foo")

        # RemovedInDjango70Warning.
        with self.subTest("Compatibility"):
            msg = "Could not create directory for saving email messages: /dev/null/foo"
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                # alias=None tells create_backend() to _omit_ the `alias` arg.
                self.create_backend(alias=None, file_path="/dev/null/foo")

    @skipIf(
        sys.platform == "win32",
        "chmod does not reliably make directories read-only on Windows.",
    )
    def test_error_if_file_path_is_not_writable(self):
        os.chmod(self.tmp_dir, 0o444)
        self.addCleanup(os.chmod, self.tmp_dir, 0o777)
        msg = f"MAILERS['test_alias']: 'file_path' is not writable: {self.tmp_dir}"
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(file_path=self.tmp_dir)

        # RemovedInDjango70Warning.
        with self.subTest("Compatibility"):
            msg = f"Could not write to directory: {self.tmp_dir}"
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                # alias=None tells create_backend() to _omit_ the `alias` arg.
                self.create_backend(alias=None, file_path=self.tmp_dir)

    def test_new_file_per_instance(self):
        # Documented behavior: "A new file is created for each new session that
        # is opened on this backend."
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(len(self.get_filenames()), 0)

        backend1 = self.create_backend()
        backend1.send_messages([email])
        self.assertEqual(len(self.get_filenames()), 1)

        backend2 = self.create_backend()
        backend2.send_messages([email])
        self.assertEqual(len(self.get_filenames()), 2)

    def test_multiple_messages_same_connection_single_file_reused(self):
        self.assertEqual(len(self.get_filenames()), 0)
        backend = self.create_backend()

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

        backend = self.create_backend()
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
    backend_class = console.EmailBackend

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

    def test_fail_silently_arg_accepted(self):
        # RemovedInDjango70Warning: remove this comment (but keep the test).
        # The console backend continues to support fail_silently. Override the
        # SharedEmailBackendTests case that treats it as deprecated.
        for value in [True, False]:
            with self.subTest(fail_silently=value):
                backend = self.create_backend(fail_silently=value)
                self.assertIs(backend.fail_silently, value)

    def test_console_stream_kwarg(self):
        s = StringIO()
        backend = self.create_backend(stream=s)
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
@ignore_warnings(
    category=RemovedInDjango70Warning, message=r"The EMAIL_\w+ setting is deprecated\."
)
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
        cls.smtp_controller.start()
        cls.addClassCleanup(cls.stop_smtp)

    @classmethod
    def stop_smtp(cls):
        cls.smtp_controller.stop()


@skipUnless(HAS_AIOSMTPD, "No aiosmtpd library detected.")
@ignore_warnings(
    category=RemovedInDjango70Warning,
    message=re.escape("Directly creating EmailBackend instances is deprecated."),
)
class SMTPBackendTests(SharedEmailBackendTests, SMTPBackendTestsBase):
    backend_class = smtp.EmailBackend

    def setUp(self):
        super().setUp()
        self.smtp_handler.flush_mailbox()
        self.addCleanup(self.smtp_handler.flush_mailbox)

    def create_backend(self, **kwargs):
        kwargs.setdefault("host", self.smtp_controller.hostname)
        kwargs.setdefault("port", self.smtp_controller.port)
        return super().create_backend(**kwargs)

    def flush_mailbox(self):
        self.smtp_handler.flush_mailbox()

    def get_mailbox_content(self):
        return self.smtp_handler.mailbox

    def get_smtp_envelopes(self):
        return self.smtp_handler.smtp_envelopes

    def test_fail_silently_arg_accepted(self):
        # RemovedInDjango70Warning: remove this comment (but keep the test).
        # The SMTP backend continues to support fail_silently. Override the
        # SharedEmailBackendTests case that treats it as deprecated.
        for value in [True, False]:
            with self.subTest(fail_silently=value):
                backend = self.create_backend(fail_silently=value)
                self.assertIs(backend.fail_silently, value)

    def test_create_from_mailers(self):
        super().test_create_from_mailers(required_options={"host": "example.com"})

    # RemovedInDjango70Warning.
    @override_settings(
        EMAIL_HOST="mail.example.com",
        EMAIL_PORT=822,
        EMAIL_HOST_USER="username",
        EMAIL_HOST_PASSWORD="password",
        EMAIL_USE_TLS=True,
        EMAIL_USE_SSL=None,
        EMAIL_SSL_CERTFILE="foo",
        EMAIL_SSL_KEYFILE="bar",
    )
    def test_ignores_settings_when_initialized_with_alias(self):
        backend = self.backend_class(alias="test_alias", host="local.mail")
        # All properties (except host) should be defaults.
        self.assertEqual(backend.host, "local.mail")
        self.assertEqual(backend.port, 25)
        self.assertIsNone(backend.username)
        self.assertIsNone(backend.password)
        self.assertIs(backend.use_tls, False)
        self.assertIs(backend.use_ssl, False)
        self.assertIsNone(backend.ssl_certfile)
        self.assertIsNone(backend.ssl_keyfile)

    # RemovedInDjango70Warning.
    def test_direct_construction_deprecated(self):
        msg = (
            "Directly creating EmailBackend instances is deprecated. Use "
            "mail.mailers instead."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            backend = self.backend_class(use_tls=True)
        # Default values come from deprecated settings without special handling
        # for port.
        self.assertEqual(backend.host, "localhost")
        self.assertEqual(backend.port, 25)

    def test_host_option_required(self):
        msg = "MAILERS['test_alias']: OPTIONS must define 'host'."
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.backend_class(alias="test_alias")

    def test_port_default_adapts_to_security(self):
        cases = [
            ("default", {}, 25),
            ("SSL", {"use_ssl": True}, 465),
            ("TLS", {"use_tls": True}, 587),
        ]
        for case, kwargs, expected_port in cases:
            with self.subTest(case):
                backend = self.backend_class(
                    alias="test_alias", host="mail.example.com", **kwargs
                )
                self.assertEqual(backend.port, expected_port)

        # RemovedInDjango70Warning: Until Django 7.0, the dynamic port default
        # applies only when initialized through mail.mailers.
        for case, kwargs, _ in cases:
            with self.subTest(f"compatibility {case}"):
                backend = self.backend_class(host="mail.example.com", **kwargs)
                self.assertEqual(backend.port, 25)

    # RemovedInDjango70Warning.
    @override_settings(
        EMAIL_HOST="mail.example.com",
        EMAIL_PORT=822,
    )
    def test_email_host_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.host, "mail.example.com")
        self.assertEqual(backend.port, 822)

    # RemovedInDjango70Warning.
    @override_settings(
        EMAIL_HOST="mail.example.com",
        EMAIL_PORT=822,
    )
    def test_email_host_override_settings(self):
        backend = smtp.EmailBackend(host="other.example.net", port=5322)
        self.assertEqual(backend.host, "other.example.net")
        self.assertEqual(backend.port, 5322)

    def test_smtp_connection_uses_host_and_port(self):
        backend = self.create_backend(host="mail.example.com", port=5322)
        self.assertEqual(backend.host, "mail.example.com")
        self.assertEqual(backend.port, 5322)
        with (
            mock.patch("django.core.mail.backends.smtp.smtplib.SMTP") as mock_smtp,
            backend,
        ):
            # Using backend as context manager opens the connection.
            pass
        mock_smtp.assert_called_once_with(
            "mail.example.com", 5322, local_hostname=mock.ANY
        )

    # RemovedInDjango70Warning.
    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password",
    )
    def test_email_authentication_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.username, "not empty username")
        self.assertEqual(backend.password, "not empty password")

    # RemovedInDjango70Warning.
    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password",
    )
    def test_email_authentication_override_settings(self):
        backend = smtp.EmailBackend(username="username", password="password")
        self.assertEqual(backend.username, "username")
        self.assertEqual(backend.password, "password")

    # RemovedInDjango70Warning.
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
        backend = self.create_backend(
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
        backend = self.create_backend()
        self.assertIsNone(backend.connection)
        opened = backend.open()
        backend.close()
        self.assertIs(opened, True)

    def test_reopen_connection(self):
        backend = self.create_backend()
        # Simulate an already open connection.
        backend.connection = mock.Mock(spec=object())
        self.assertIs(backend.open(), False)

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertIs(backend.use_tls, True)

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_override_settings(self):
        backend = smtp.EmailBackend(use_tls=False)
        self.assertIs(backend.use_tls, False)

    def test_email_tls_default_disabled(self):
        backend = self.create_backend()
        self.assertIs(backend.use_tls, False)

    def test_ssl_tls_mutually_exclusive(self):
        msg = (
            "MAILERS['test_alias']: The 'use_ssl' and 'use_tls' "
            "OPTIONS are incompatible. Set at most one of them to True."
        )
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(use_ssl=True, use_tls=True)

    # RemovedInDjango70Warning.
    def test_ssl_tls_settings_mutually_exclusive(self):
        msg = (
            "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
            "one of those settings to True."
        )
        with (
            self.settings(EMAIL_USE_SSL=True, EMAIL_USE_TLS=True),
            self.assertRaisesMessage(ValueError, msg),
        ):
            smtp.EmailBackend()

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertIs(backend.use_ssl, True)

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_override_settings(self):
        backend = smtp.EmailBackend(use_ssl=False)
        self.assertIs(backend.use_ssl, False)

    def test_email_ssl_default_disabled(self):
        backend = self.create_backend()
        self.assertIs(backend.use_ssl, False)

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_SSL_CERTFILE="foo")
    def test_email_ssl_certfile_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_certfile, "foo")

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_SSL_CERTFILE="foo")
    def test_email_ssl_certfile_override_settings(self):
        backend = smtp.EmailBackend(ssl_certfile="bar")
        self.assertEqual(backend.ssl_certfile, "bar")

    def test_email_ssl_certfile_default_disabled(self):
        backend = self.create_backend()
        self.assertIsNone(backend.ssl_certfile)

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_SSL_KEYFILE="foo")
    def test_email_ssl_keyfile_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_keyfile, "foo")

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_SSL_KEYFILE="foo")
    def test_email_ssl_keyfile_override_settings(self):
        backend = smtp.EmailBackend(ssl_keyfile="bar")
        self.assertEqual(backend.ssl_keyfile, "bar")

    def test_email_ssl_keyfile_default_disabled(self):
        backend = self.create_backend()
        self.assertIsNone(backend.ssl_keyfile)

    def test_ssl_context_uses_ssl_certfile_and_keyfile(self):
        backend = self.create_backend(ssl_certfile="certfile", ssl_keyfile="keyfile")
        with mock.patch(
            "django.core.mail.backends.smtp.ssl.SSLContext"
        ) as mock_ssl_context:
            ssl_context = backend.ssl_context
        self.assertIs(ssl_context, mock_ssl_context.return_value)
        mock_ssl_context.assert_called_once_with(protocol=ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.load_cert_chain.assert_called_once_with("certfile", "keyfile")

    def test_email_tls_attempts_starttls(self):
        backend = self.create_backend(use_tls=True)
        self.assertIs(backend.use_tls, True)
        with self.assertRaisesMessage(
            SMTPException, "STARTTLS extension not supported by server."
        ):
            with backend:
                pass

    def test_email_ssl_attempts_ssl_connection(self):
        backend = self.create_backend(use_ssl=True)
        self.assertIs(backend.use_ssl, True)
        with self.assertRaises(SSLError):
            with backend:
                pass

    def test_connection_timeout_default(self):
        backend = self.create_backend()
        self.assertIsNone(backend.timeout)

    def test_connection_timeout_custom(self):
        """The timeout parameter can be customized."""

        class MyEmailBackend(smtp.EmailBackend):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("timeout", 42)
                super().__init__(*args, **kwargs)

        myemailbackend = MyEmailBackend(
            host=self.smtp_controller.hostname, port=self.smtp_controller.port
        )
        myemailbackend.open()
        self.assertEqual(myemailbackend.timeout, 42)
        self.assertEqual(myemailbackend.connection.timeout, 42)
        myemailbackend.close()

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_TIMEOUT=10)
    def test_email_timeout_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.timeout, 10)

    # RemovedInDjango70Warning.
    @override_settings(EMAIL_TIMEOUT=10)
    def test_email_timeout_override_settings(self):
        backend = smtp.EmailBackend(timeout=15)
        self.assertEqual(backend.timeout, 15)

    def test_smtp_connection_uses_timeout(self):
        backend = self.create_backend(timeout=10)
        with backend:
            self.assertEqual(backend.connection.timeout, 10)

    def test_serialized_message_uses_crlf_line_ending(self):
        backend = self.create_backend()
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
        backend = self.create_backend()
        # Simulate connection initialization success and a subsequent
        # connection exception.
        backend.connection = mock.Mock()
        backend.open = lambda: None
        email = EmailMessage(to=["to@example.com"])
        self.assertEqual(backend.send_messages([email]), 0)

    def test_send_messages_with_empty_list_does_not_open_connection(self):
        backend = self.create_backend()
        backend.open = mock.Mock()
        self.assertEqual(backend.send_messages([]), 0)
        backend.open.assert_not_called()

    def test_send_messages_zero_sent(self):
        """A message isn't sent if it doesn't have any recipients."""
        backend = self.create_backend()
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
        backend = self.create_backend()
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
        backend = self.create_backend()
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
        backend = self.create_backend()
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
        # The SMTP EmailBackend must work around invalid email encoding caused
        # by https://github.com/python/cpython/issues/122476 (#35713).
        try:
            # Detect fix for CPython issue gh-122476.
            message = PyEmailMessage()
            message["To"] = "nø@example.dk"
            message.as_bytes()
        except HeaderWriteError:
            # PY315: Error from Python email generator.
            msg = "Non-ASCII local-part 'nø' is invalid"
        else:
            # Python <=3.14: Error from smtp.EmailBackend.prep_address().
            msg = (
                "Invalid address 'nø@example.dk': local-part contains "
                "non-ASCII characters"
            )

        backend = self.create_backend()
        email = EmailMessage(to=["nø@example.dk"])
        with self.assertRaisesMessage((ValueError, HeaderWriteError), msg):
            backend.send_messages([email])

    def test_prep_address_without_force_ascii(self):
        # A subclass implementing SMTPUTF8 could use
        # prep_address(force_ascii=False).
        backend = self.create_backend()
        for case in ["åh@example.dk", "oh@åh.example.dk", "åh@åh.example.dk"]:
            with self.subTest(case=case):
                self.assertEqual(backend.prep_address(case, force_ascii=False), case)


@skipUnless(HAS_AIOSMTPD, "No aiosmtpd library detected.")
class SMTPBackendStoppedServerTests(SMTPBackendTestsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # RemovedInDjango70Warning: alias argument can be removed (needed
        # during mail.mailers transition to prevent compatibility mode).
        cls.backend = smtp.EmailBackend(
            alias="test_alias",
            host=cls.smtp_controller.hostname,
            port=cls.smtp_controller.port,
        )
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
