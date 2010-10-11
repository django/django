# coding: utf-8
import email
import os
import shutil
import sys
import tempfile
from StringIO import StringIO
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage, mail_admins, mail_managers, EmailMultiAlternatives
from django.core.mail import send_mail, send_mass_mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends import console, dummy, locmem, filebased, smtp
from django.core.mail.message import BadHeaderError
from django.test import TestCase
from django.utils.translation import ugettext_lazy

class MailTests(TestCase):

    def test_ascii(self):
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'])
        message = email.message()
        self.assertEqual(message['Subject'].encode(), 'Subject')
        self.assertEqual(message.get_payload(), 'Content')
        self.assertEqual(message['From'], 'from@example.com')
        self.assertEqual(message['To'], 'to@example.com')

    def test_multiple_recipients(self):
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com','other@example.com'])
        message = email.message()
        self.assertEqual(message['Subject'].encode(), 'Subject')
        self.assertEqual(message.get_payload(), 'Content')
        self.assertEqual(message['From'], 'from@example.com')
        self.assertEqual(message['To'], 'to@example.com, other@example.com')

    def test_cc(self):
        """Regression test for #7722"""
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'], cc=['cc@example.com'])
        message = email.message()
        self.assertEqual(message['Cc'], 'cc@example.com')
        self.assertEqual(email.recipients(), ['to@example.com', 'cc@example.com'])

        # Verify headers
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        connection = console.EmailBackend()
        connection.send_messages([email])
        self.assertTrue(sys.stdout.getvalue().startswith('Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: Subject\nFrom: from@example.com\nTo: to@example.com\nCc: cc@example.com\nDate: '))
        sys.stdout = old_stdout

        # Test multiple CC with multiple To
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com', 'other@example.com'], cc=['cc@example.com', 'cc.other@example.com'])
        message = email.message()
        self.assertEqual(message['Cc'], 'cc@example.com, cc.other@example.com')
        self.assertEqual(email.recipients(), ['to@example.com', 'other@example.com', 'cc@example.com', 'cc.other@example.com'])

        # Testing with Bcc
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com', 'other@example.com'], cc=['cc@example.com', 'cc.other@example.com'], bcc=['bcc@example.com'])
        message = email.message()
        self.assertEqual(message['Cc'], 'cc@example.com, cc.other@example.com')
        self.assertEqual(email.recipients(), ['to@example.com', 'other@example.com', 'cc@example.com', 'cc.other@example.com', 'bcc@example.com'])

    def test_header_injection(self):
        email = EmailMessage('Subject\nInjection Test', 'Content', 'from@example.com', ['to@example.com'])
        self.assertRaises(BadHeaderError, email.message)
        email = EmailMessage(ugettext_lazy('Subject\nInjection Test'), 'Content', 'from@example.com', ['to@example.com'])
        self.assertRaises(BadHeaderError, email.message)

    def test_space_continuation(self):
        """
        Test for space continuation character in long (ascii) subject headers (#7747)
        """
        email = EmailMessage('Long subject lines that get wrapped should use a space continuation character to get expected behaviour in Outlook and Thunderbird', 'Content', 'from@example.com', ['to@example.com'])
        message = email.message()
        self.assertEqual(message['Subject'], 'Long subject lines that get wrapped should use a space continuation\n character to get expected behaviour in Outlook and Thunderbird')

    def test_message_header_overrides(self):
        """
        Specifying dates or message-ids in the extra headers overrides the
        default values (#9233)
        """
        headers = {"date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        email = EmailMessage('subject', 'content', 'from@example.com', ['to@example.com'], headers=headers)
        self.assertEqual(email.message().as_string(), 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: subject\nFrom: from@example.com\nTo: to@example.com\ndate: Fri, 09 Nov 2001 01:08:47 -0000\nMessage-ID: foo\n\ncontent')

    def test_empty_admins(self):
        """
        Test that mail_admins/mail_managers doesn't connect to the mail server
        if there are no recipients (#9383)
        """
        old_admins = settings.ADMINS
        old_managers = settings.MANAGERS

        settings.ADMINS = settings.MANAGERS = [('nobody','nobody@example.com')]
        mail.outbox = []
        mail_admins('hi', 'there')
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []
        mail_managers('hi', 'there')
        self.assertEqual(len(mail.outbox), 1)

        settings.ADMINS = settings.MANAGERS = []
        mail.outbox = []
        mail_admins('hi', 'there')
        self.assertEqual(len(mail.outbox), 0)
        mail.outbox = []
        mail_managers('hi', 'there')
        self.assertEqual(len(mail.outbox), 0)

        settings.ADMINS = old_admins
        settings.MANAGERS = old_managers

    def test_from_header(self):
        """
        Make sure we can manually set the From header (#9214)
        """
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        message = email.message()
        self.assertEqual(message['From'], 'from@example.com')

    def test_multiple_message_call(self):
        """
        Regression for #13259 - Make sure that headers are not changed when
        calling EmailMessage.message()
        """
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        message = email.message()
        self.assertEqual(message['From'], 'from@example.com')
        message = email.message()
        self.assertEqual(message['From'], 'from@example.com')

    def test_unicode_header(self):
        """
        Regression for #11144 - When a to/from/cc header contains unicode,
        make sure the email addresses are parsed correctly (especially with
        regards to commas)
        """
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['"Firstname Sürname" <to@example.com>','other@example.com'])
        self.assertEqual(email.message()['To'], '=?utf-8?q?Firstname_S=C3=BCrname?= <to@example.com>, other@example.com')
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['"Sürname, Firstname" <to@example.com>','other@example.com'])
        self.assertEqual(email.message()['To'], '=?utf-8?q?S=C3=BCrname=2C_Firstname?= <to@example.com>, other@example.com')

    def test_safe_mime_multipart(self):
        """
        Make sure headers can be set with a different encoding than utf-8 in
        SafeMIMEMultipart as well
        """
        headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        subject, from_email, to = 'hello', 'from@example.com', '"Sürname, Firstname" <to@example.com>'
        text_content = 'This is an important message.'
        html_content = '<p>This is an <strong>important</strong> message.</p>'
        msg = EmailMultiAlternatives('Message from Firstname Sürname', text_content, from_email, [to], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.encoding = 'iso-8859-1'
        self.assertEqual(msg.message()['To'], '=?iso-8859-1?q?S=FCrname=2C_Firstname?= <to@example.com>')
        self.assertEqual(msg.message()['Subject'].encode(), u'=?iso-8859-1?q?Message_from_Firstname_S=FCrname?=')

    def test_encoding(self):
        """
        Regression for #12791 - Encode body correctly with other encodings
        than utf-8
        """
        email = EmailMessage('Subject', 'Firstname Sürname is a great guy.', 'from@example.com', ['other@example.com'])
        email.encoding = 'iso-8859-1'
        message = email.message()
        self.assertTrue(message.as_string().startswith('Content-Type: text/plain; charset="iso-8859-1"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: Subject\nFrom: from@example.com\nTo: other@example.com'))
        self.assertEqual(message.get_payload(), 'Firstname S=FCrname is a great guy.')

        # Make sure MIME attachments also works correctly with other encodings than utf-8
        text_content = 'Firstname Sürname is a great guy.'
        html_content = '<p>Firstname Sürname is a <strong>great</strong> guy.</p>'
        msg = EmailMultiAlternatives('Subject', text_content, 'from@example.com', ['to@example.com'])
        msg.encoding = 'iso-8859-1'
        msg.attach_alternative(html_content, "text/html")
        self.assertEqual(msg.message().get_payload(0).as_string(), 'Content-Type: text/plain; charset="iso-8859-1"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\n\nFirstname S=FCrname is a great guy.')
        self.assertEqual(msg.message().get_payload(1).as_string(), 'Content-Type: text/html; charset="iso-8859-1"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\n\n<p>Firstname S=FCrname is a <strong>great</strong> guy.</p>')

    def test_attachments(self):
        """Regression test for #9367"""
        headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        subject, from_email, to = 'hello', 'from@example.com', 'to@example.com'
        text_content = 'This is an important message.'
        html_content = '<p>This is an <strong>important</strong> message.</p>'
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.attach("an attachment.pdf", "%PDF-1.4.%...", mimetype="application/pdf")
        msg_str = msg.message().as_string()
        message = email.message_from_string(msg_str)
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_content_type(), 'multipart/mixed')
        self.assertEqual(message.get_default_type(), 'text/plain')
        payload = message.get_payload()
        self.assertEqual(payload[0].get_content_type(), 'multipart/alternative')
        self.assertEqual(payload[1].get_content_type(), 'application/pdf')

    def test_arbitrary_stream(self):
        """
        Test that the console backend can be pointed at an arbitrary stream.
        """
        s = StringIO()
        connection = mail.get_connection('django.core.mail.backends.console.EmailBackend', stream=s)
        send_mail('Subject', 'Content', 'from@example.com', ['to@example.com'], connection=connection)
        self.assertTrue(s.getvalue().startswith('Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: Subject\nFrom: from@example.com\nTo: to@example.com\nDate: '))

    def test_stdout(self):
        """Make sure that the console backend writes to stdout by default"""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        connection = console.EmailBackend()
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        connection.send_messages([email])
        self.assertTrue(sys.stdout.getvalue().startswith('Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: Subject\nFrom: from@example.com\nTo: to@example.com\nDate: '))
        sys.stdout = old_stdout

    def test_dummy(self):
        """
        Make sure that dummy backends returns correct number of sent messages
        """
        connection = dummy.EmailBackend()
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        self.assertEqual(connection.send_messages([email, email, email]), 3)

    def test_locmem(self):
        """
        Make sure that the locmen backend populates the outbox.
        """
        mail.outbox = []
        connection = locmem.EmailBackend()
        email1 = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        email2 = EmailMessage('Subject 2', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        connection.send_messages([email1, email2])
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, 'Subject')
        self.assertEqual(mail.outbox[1].subject, 'Subject 2')
        
        # Make sure that multiple locmem connections share mail.outbox
        mail.outbox = []
        connection2 = locmem.EmailBackend()
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        connection.send_messages([email])
        connection2.send_messages([email])
        self.assertEqual(len(mail.outbox), 2)

    def test_file_backend(self):
        tmp_dir = tempfile.mkdtemp()
        connection = filebased.EmailBackend(file_path=tmp_dir)
        email1 = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        connection.send_messages([email1])
        self.assertEqual(len(os.listdir(tmp_dir)), 1)
        message = email.message_from_file(open(os.path.join(tmp_dir, os.listdir(tmp_dir)[0])))
        self.assertEqual(message.get_content_type(), 'text/plain')
        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get('from'), 'from@example.com')
        self.assertEqual(message.get('to'), 'to@example.com')
        connection2 = filebased.EmailBackend(file_path=tmp_dir)
        connection2.send_messages([email1])
        self.assertEqual(len(os.listdir(tmp_dir)), 2)
        connection.send_messages([email1])
        self.assertEqual(len(os.listdir(tmp_dir)), 2)
        email1.connection = filebased.EmailBackend(file_path=tmp_dir)
        connection_created = connection.open()
        email1.send()
        self.assertEqual(len(os.listdir(tmp_dir)), 3)
        email1.send()
        self.assertEqual(len(os.listdir(tmp_dir)), 3)
        connection.close()
        shutil.rmtree(tmp_dir)

    def test_arbitrary_keyword(self):
        """
        Make sure that get_connection() accepts arbitrary keyword that might be
        used with custom backends.
        """
        c = mail.get_connection(fail_silently=True, foo='bar')
        self.assertTrue(c.fail_silently)

    def test_custom_backend(self):
        """Test custom backend defined in this suite."""
        conn = mail.get_connection('regressiontests.mail.custombackend.EmailBackend')
        self.assertTrue(hasattr(conn, 'test_outbox'))
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        conn.send_messages([email])
        self.assertEqual(len(conn.test_outbox), 1)

    def test_backend_arg(self):
        """Test backend argument of mail.get_connection()"""
        self.assertTrue(isinstance(mail.get_connection('django.core.mail.backends.smtp.EmailBackend'), smtp.EmailBackend))
        self.assertTrue(isinstance(mail.get_connection('django.core.mail.backends.locmem.EmailBackend'), locmem.EmailBackend))
        self.assertTrue(isinstance(mail.get_connection('django.core.mail.backends.dummy.EmailBackend'), dummy.EmailBackend))
        self.assertTrue(isinstance(mail.get_connection('django.core.mail.backends.console.EmailBackend'), console.EmailBackend))
        tmp_dir = tempfile.mkdtemp()
        self.assertTrue(isinstance(mail.get_connection('django.core.mail.backends.filebased.EmailBackend', file_path=tmp_dir), filebased.EmailBackend))
        shutil.rmtree(tmp_dir)
        self.assertTrue(isinstance(mail.get_connection(), locmem.EmailBackend))

    def test_connection_arg(self):
        """Test connection argument to send_mail(), et. al."""
        connection = mail.get_connection('django.core.mail.backends.locmem.EmailBackend')

        mail.outbox = []
        send_mail('Subject', 'Content', 'from@example.com', ['to@example.com'], connection=connection)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])

        mail.outbox = []
        send_mass_mail([
                ('Subject1', 'Content1', 'from1@example.com', ['to1@example.com']),
                ('Subject2', 'Content2', 'from2@example.com', ['to2@example.com'])
            ], connection=connection)
        self.assertEqual(len(mail.outbox), 2)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Subject1')
        self.assertEqual(message.from_email, 'from1@example.com')
        self.assertEqual(message.to, ['to1@example.com'])
        message = mail.outbox[1]
        self.assertEqual(message.subject, 'Subject2')
        self.assertEqual(message.from_email, 'from2@example.com')
        self.assertEqual(message.to, ['to2@example.com'])

        old_admins = settings.ADMINS
        old_managers = settings.MANAGERS
        settings.ADMINS = settings.MANAGERS = [('nobody','nobody@example.com')]

        mail.outbox = []
        mail_admins('Subject', 'Content', connection=connection)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, '[Django] Subject')
        self.assertEqual(message.from_email, 'root@localhost')
        self.assertEqual(message.to, ['nobody@example.com'])

        mail.outbox = []
        mail_managers('Subject', 'Content', connection=connection)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, '[Django] Subject')
        self.assertEqual(message.from_email, 'root@localhost')
        self.assertEqual(message.to, ['nobody@example.com'])

        settings.ADMINS = old_admins
        settings.MANAGERS = old_managers

    def test_mail_prefix(self):
        """Test prefix argument in manager/admin mail."""
        # Regression for #13494.
        old_admins = settings.ADMINS
        old_managers = settings.MANAGERS
        settings.ADMINS = settings.MANAGERS = [('nobody','nobody@example.com')]

        mail_managers(ugettext_lazy('Subject'), 'Content')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, '[Django] Subject')

        mail.outbox = []
        mail_admins(ugettext_lazy('Subject'), 'Content')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, '[Django] Subject')

        settings.ADMINS = old_admins
        settings.MANAGERS = old_managers
