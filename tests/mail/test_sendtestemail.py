from __future__ import unicode_literals

from django.core import mail
from django.core.management import call_command
from django.test import SimpleTestCase


class SendTestEmailManagementCommand(SimpleTestCase):
    """
    Test the sending of a test email using the `sendtestemail` command.
    """

    def test_send_test_email(self):
        """
        The mail is sent with the correct subject and recipient.
        """
        recipient = "joe@example.com"
        call_command("sendtestemail", recipient)
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(mail_message.subject[0:15], 'Test email from')
        self.assertEqual(mail_message.recipients(), [recipient])

    def test_send_test_email_with_multiple_addresses(self):
        """
        The mail may be sent with multiple recipients.
        """
        recipients = ["joe@example.com", "jane@example.com"]
        call_command("sendtestemail", recipients[0], recipients[1])
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(mail_message.subject[0:15], 'Test email from')
        self.assertEqual(mail_message.recipients(), recipients)
