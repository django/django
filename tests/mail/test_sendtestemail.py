from __future__ import unicode_literals

from django.core import mail
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


@override_settings(
    ADMINS=(('Admin', 'admin@example.com'), ('Admin and Manager (Admin)', 'admin_and_manager@example.com')),
    MANAGERS=(('Manager', 'manager@example.com'), ('Admin and Manager (Manager)', 'admin_and_manager@example.com')),
)
class SendTestEmailManagementCommand(SimpleTestCase):
    """
    Test the sending of a test email using the `sendtestemail` command.
    """

    def test_single_receiver(self):
        """
        The mail is sent with the correct subject and recipient.
        """
        recipient = 'joe@example.com'
        call_command('sendtestemail', recipient)
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(mail_message.subject[0:15], 'Test email from')
        self.assertEqual(mail_message.recipients(), [recipient])

    def test_multiple_receivers(self):
        """
        The mail may be sent with multiple recipients.
        """
        recipients = ['joe@example.com', 'jane@example.com']
        call_command('sendtestemail', recipients[0], recipients[1])
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(mail_message.subject[0:15], 'Test email from')
        self.assertEqual(sorted(mail_message.recipients()), [
            'jane@example.com',
            'joe@example.com',
        ])

    def test_manager_receivers(self):
        """
        The mail should be sent to the email addresses specified in
        settings.MANAGERS.
        """
        call_command('sendtestemail', '--managers')
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(sorted(mail_message.recipients()), [
            'admin_and_manager@example.com',
            'manager@example.com',
        ])

    def test_admin_receivers(self):
        """
        The mail should be sent to the email addresses specified in
        settings.ADMIN.
        """
        call_command('sendtestemail', '--admins')
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(sorted(mail_message.recipients()), [
            'admin@example.com',
            'admin_and_manager@example.com',
        ])

    def test_manager_and_admin_receivers(self):
        """
        The mail should be sent to the email addresses specified in both
        settings.MANAGERS and settings.ADMINS.
        """
        call_command('sendtestemail', '--managers', '--admins')
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(sorted(mail_message.recipients()), [
            'admin@example.com',
            'admin_and_manager@example.com',
            'manager@example.com',
        ])
