# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from django.utils.six import StringIO


class SendTestEmailManagementCommand(SimpleTestCase):
    """
    Test the sending of a test email using the `sendtestemail` command.
    """

    def test_send_test_email(self):
        """
        The mail is sent with the correct subject and recipient.
        """
        recipient = "joe@somewhere.org"
        call_command("sendtestemail", recipient)
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(mail_message.subject[0:15], 'Test email from')
        self.assertEqual(mail_message.recipients(), [recipient])

    def test_send_test_email_with_multiple_addresses(self):
        """
        The mail may be sent with multiple recipients.
        """
        recipients = ["joe@somewhere.org", "jane@elsewhere.net"]
        call_command("sendtestemail", recipients[0], recipients[1])
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEqual(mail_message.subject[0:15], 'Test email from')
        self.assertEqual(mail_message.recipients(), recipients)

    def test_send_test_email_missing_recipient(self):
        """
        A CommandError is raised if no recipients are specified.
        """
        with self.assertRaisesMessage(CommandError, 'You must provide at least one destination email'):
            call_command("sendtestemail")
