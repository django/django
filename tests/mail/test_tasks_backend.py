import json
import random
from datetime import datetime, timezone
from email.message import MIMEPart
from unittest import mock

from django.core import mail
from django.core.mail import (
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
    InvalidMailer,
)
from django.core.mail.backends import tasks
from django.core.mail.serialization import (
    SERIALIZATION_VERSION,
    deserialize_message,
    serialize_message,
)
from django.tasks import TaskResultStatus, task_backends
from django.test import SimpleTestCase, override_settings
from django.utils.translation import gettext_lazy

from .test_backends import SharedEmailBackendTests


@override_settings(
    MAILERS={
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
        "locmem": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
    },
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
            "QUEUES": [],
        },
        "dummy": {
            "BACKEND": "django.tasks.backends.dummy.DummyBackend",
            "QUEUES": [],
        },
    },
)
class TasksBackendTests(SharedEmailBackendTests, SimpleTestCase):
    backend_class = tasks.EmailBackend

    def create_backend(self, **kwargs):
        kwargs.setdefault("mailer", "locmem")
        return super().create_backend(**kwargs)

    def get_mailbox_content(self):
        return [m.message() for m in mail.outbox]

    def flush_mailbox(self):
        mail.outbox = []

    def tearDown(self):
        super().tearDown()
        mail.outbox = []
        task_backends["dummy"].clear()

    def test_create_from_mailers(self):
        with self.settings(
            MAILERS={
                "custom": {
                    "BACKEND": "django.core.mail.backends.tasks.EmailBackend",
                    "OPTIONS": {"mailer": "locmem"},
                },
                "locmem": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
            }
        ):
            backend = mail.mailers["custom"]
            self.assertIsInstance(backend, tasks.EmailBackend)
            self.assertEqual(backend.alias, "custom")
            self.assertEqual(backend.mailer, "locmem")

    def test_mailer_option_required(self):
        msg = "MAILERS['test_alias']: The 'mailer' option is required."
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(mailer=None)

    def test_mailer_option_cannot_refer_to_itself(self):
        msg = (
            "MAILERS['test_alias']: The 'mailer' option cannot refer to its own "
            "mailer."
        )
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(mailer="test_alias")

    def test_mailer_option_unknown(self):
        msg = (
            "MAILERS['test_alias']: The 'mailer' option refers to an unknown "
            "mailer 'unknown'."
        )
        with self.assertRaisesMessage(InvalidMailer, msg):
            self.create_backend(mailer="unknown")

    def test_sent_using_target_mailer(self):
        email = EmailMessage(to=["to@example.com"])
        self.create_backend().send_messages([email])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].sent_using, "locmem")

    def test_messages_without_recipients_not_enqueued(self):
        backend = self.create_backend(task_backend="dummy")
        self.assertEqual(backend.send_messages([EmailMessage()]), 0)
        self.assertEqual(backend.send_messages([]), 0)
        self.assertEqual(task_backends["dummy"].results, [])

    def test_send_messages_returns_zero_when_queued(self):
        backend = self.create_backend(task_backend="dummy")
        emails = [
            EmailMessage(to=["to-1@example.com"]),
            EmailMessage(),
            EmailMessage(to=["to-2@example.com"]),
        ]
        self.assertEqual(backend.send_messages(emails), 0)
        [result] = task_backends["dummy"].results
        self.assertEqual(len(result.args[1]), 2)

    def test_send_messages_returns_sent_count(self):
        backend = self.create_backend()
        emails = [
            EmailMessage(to=["to-1@example.com"]),
            EmailMessage(to=["to-2@example.com"]),
        ]

        with mock.patch(
            "django.core.mail.backends.locmem.EmailBackend.send_messages",
            return_value=1,
        ) as send_messages:
            self.assertEqual(backend.send_messages(emails), 1)
        send_messages.assert_called_once()

    def test_enqueue_options(self):
        backend = self.create_backend(
            task_backend="dummy", queue_name="emails", priority=10
        )
        emails = [
            EmailMessage("Subject 1", to=["to-1@example.com"]),
            EmailMessage("Subject 2", to=["to-2@example.com"]),
        ]
        self.assertEqual(backend.send_messages(emails), 0)
        self.assertEqual(mail.outbox, [])

        [result] = task_backends["dummy"].results
        self.assertEqual(result.status, TaskResultStatus.READY)
        self.assertEqual(result.backend, "dummy")
        self.assertEqual(result.task.queue_name, "emails")
        self.assertEqual(result.task.priority, 10)
        self.assertEqual(
            result.args,
            ["locmem", [serialize_message(email) for email in emails]],
        )

        # Running the task sends the messages using the target mailer.
        self.assertEqual(result.task.call(*result.args), 2)
        self.assertEqual([m.subject for m in mail.outbox], ["Subject 1", "Subject 2"])
        self.assertEqual([m.sent_using for m in mail.outbox], ["locmem", "locmem"])

    def test_failure_raised(self):
        # The locmem backend validates headers (#18861).
        email = EmailMessage(subject="Subject\nMultiline", to=["to@example.com"])
        backend = self.create_backend()
        self.assertEqual(backend.send_messages([email]), 0)
        self.assertEqual(mail.outbox, [])

    def test_original_message_not_mutated(self):
        email = EmailMessage("Subject", "Body", to=["to@example.com"])
        before = serialize_message(email)
        self.create_backend().send_messages([email])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(serialize_message(email), before)
        self.assertFalse(hasattr(email, "sent_using"))


class CustomEmailMessage(EmailMessage):
    pass


class SerializationTests(SimpleTestCase):
    def roundtrip(self, email):
        data = serialize_message(email)
        # The serialized data must survive a JSON round trip.
        return deserialize_message(json.loads(json.dumps(data)))

    def as_bytes(self, email):
        # A fixed Message-ID and seeded MIME boundaries make the output
        # deterministic.
        with mock.patch("email.generator.random", random.Random(0)):
            return email.message().as_bytes()

    def assertRoundTrips(self, email):
        email.extra_headers.setdefault("Message-ID", "<id@example.com>")
        result = self.roundtrip(email)
        self.assertIs(type(result), type(email))
        self.assertEqual(self.as_bytes(result), self.as_bytes(email))
        return result

    def test_basic(self):
        email = EmailMessage(
            "Subject",
            "Body\n",
            "from@example.com",
            ["to@example.com"],
            bcc=["bcc@example.com"],
            cc=["cc@example.com"],
            reply_to=["reply@example.com"],
            headers={"X-Custom": "value"},
        )
        result = self.assertRoundTrips(email)
        self.assertEqual(
            result.recipients(),
            ["to@example.com", "cc@example.com", "bcc@example.com"],
        )
        self.assertEqual(result.reply_to, ["reply@example.com"])

    def test_unicode(self):
        email = EmailMessage(
            "Chère maman",
            "Je t'aime très fort\n",
            "Firstname Sürname <from@example.com>",
            ["Jörg <to@example.com>"],
        )
        result = self.assertRoundTrips(email)
        self.assertEqual(result.subject, "Chère maman")

    def test_lazy_strings(self):
        email = EmailMessage(
            gettext_lazy("Subject"),
            gettext_lazy("Body"),
            gettext_lazy("from@example.com"),
            [gettext_lazy("to@example.com")],
        )
        data = serialize_message(email)
        self.assertEqual(data["subject"], "Subject")
        self.assertEqual(data["body"], "Body")
        self.assertEqual(data["from_email"], "from@example.com")
        self.assertEqual(data["to"], ["to@example.com"])
        self.assertRoundTrips(email)

    def test_date_header_datetime(self):
        date = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        email = EmailMessage(to=["to@example.com"], headers={"Date": date})
        result = self.assertRoundTrips(email)
        self.assertEqual(result.message()["Date"].datetime, date)

    def test_content_subtype_and_encoding(self):
        email = EmailMessage("Subject", "<p>Hé</p>", to=["to@example.com"])
        email.content_subtype = "html"
        email.encoding = "iso-8859-1"
        result = self.assertRoundTrips(email)
        self.assertEqual(result.content_subtype, "html")
        self.assertEqual(result.encoding, "iso-8859-1")

    def test_alternatives(self):
        email = EmailMultiAlternatives("Subject", "Text", to=["to@example.com"])
        email.attach_alternative("<p>HTML</p>", "text/html")
        email.attach_alternative(b"binary", "application/octet-stream")
        result = self.assertRoundTrips(email)
        self.assertEqual(
            result.alternatives,
            [
                EmailAlternative("<p>HTML</p>", "text/html"),
                EmailAlternative(b"binary", "application/octet-stream"),
            ],
        )
        self.assertIsInstance(result.alternatives[0], EmailAlternative)

    def test_attachments(self):
        email = EmailMessage(to=["to@example.com"])
        email.attach("file.txt", "Text content", "text/plain")
        email.attach("file.bin", b"\x00\x01\xff", "application/octet-stream")
        email.attach(("utf-8", "", "fïlé.txt"), "Content", "text/plain")
        result = self.assertRoundTrips(email)
        self.assertEqual(
            result.attachments,
            [
                EmailAttachment("file.txt", "Text content", "text/plain"),
                EmailAttachment(
                    "file.bin", b"\x00\x01\xff", "application/octet-stream"
                ),
                EmailAttachment(("utf-8", "", "fïlé.txt"), "Content", "text/plain"),
            ],
        )
        self.assertIsInstance(result.attachments[0], EmailAttachment)

    def test_mimepart_attachment(self):
        part = MIMEPart()
        part.set_content("Part content\n", disposition="attachment")
        email = EmailMessage(to=["to@example.com"])
        email.attach(part)
        result = self.assertRoundTrips(email)
        [attachment] = result.attachments
        self.assertIsInstance(attachment, MIMEPart)
        self.assertEqual(attachment.get_content(), "Part content\n")

    def test_attached_email_message(self):
        inner = EmailMessage(
            "Inner", "Inner body", "inner@example.com", ["to@example.com"]
        )
        inner.extra_headers["Message-ID"] = "<inner@example.com>"
        email = EmailMessage(to=["to@example.com"])
        email.attach(None, inner, "message/rfc822")
        result = self.assertRoundTrips(email)
        [attachment] = result.attachments
        self.assertIsInstance(attachment.content, EmailMessage)
        self.assertEqual(attachment.content.subject, "Inner")
        self.assertEqual(attachment.mimetype, "message/rfc822")

    def test_subclass_preserved(self):
        email = CustomEmailMessage("Subject", to=["to@example.com"])
        result = self.assertRoundTrips(email)
        self.assertIs(type(result), CustomEmailMessage)

    def test_json_serializable(self):
        email = EmailMultiAlternatives("Subject", "Body", to=["to@example.com"])
        email.attach_alternative("<p>HTML</p>", "text/html")
        email.attach("file.bin", b"\x00", "application/octet-stream")
        data = serialize_message(email)
        self.assertEqual(json.loads(json.dumps(data)), data)
        self.assertEqual(data["version"], SERIALIZATION_VERSION)

    def test_not_email_message(self):
        msg = "message must be an EmailMessage, not 'str'."
        with self.assertRaisesMessage(TypeError, msg):
            serialize_message("not a message")

    def test_unsupported_version(self):
        data = serialize_message(EmailMessage())
        for version in [None, 0, SERIALIZATION_VERSION + 1]:
            with self.subTest(version=version):
                data["version"] = version
                msg = f"Unsupported email serialization version {version!r}."
                with self.assertRaisesMessage(ValueError, msg):
                    deserialize_message(data)

    def test_class_not_email_message(self):
        data = serialize_message(EmailMessage())
        for class_path in ["email.message.EmailMessage", "json.dumps"]:
            with self.subTest(class_path=class_path):
                data["class"] = class_path
                msg = f"{class_path!r} is not an EmailMessage subclass."
                with self.assertRaisesMessage(ValueError, msg):
                    deserialize_message(data)
