# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from django.utils.six import StringIO


class SendTestEmailManagementCommand(SimpleTestCase):
    """
    Test the sending of a test email using management command "sendtestemail"
    """

    def test_send_test_email(self):
        """
        Test that mail is sent with the correct subject and recipient.
        """
        new_io = StringIO()
        recipient = "joe@somewhere.org"
        call_command("sendtestemail", recipient, stdout=new_io)
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEquals(mail_message.subject[0:15], 'Test email from')
        self.assertEquals(mail_message.recipients(), ["joe@somewhere.org"])

    def test_send_test_email_with_multiple_addresses(self):
        """
        Test that the mail is sent with multiple recipients
        """
        new_io = StringIO()
        recipients = ["joe@somewhere.org", "jane@elsewhere.net"]
        call_command("sendtestemail", recipients[0], recipients[1], stdout=new_io)
        self.assertEqual(len(mail.outbox), 1)
        mail_message = mail.outbox[0]
        self.assertEquals(mail_message.subject[0:15], 'Test email from')
        self.assertEquals(mail_message.recipients(), recipients)

    def test_send_test_email_missing_recipient(self):
        """
        Test that the right error is raised if a recipient is omitted.
        """
        new_io = StringIO()
        with self.assertRaisesMessage(CommandError, 'You must provide at least one destination email'):
            call_command("sendtestemail", stdout=new_io)
