# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import asyncore
import os
import shutil
import smtpd
import sys
import tempfile
import threading
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPException
from ssl import SSLError

from django.core import mail
from django.core.mail import (
    EmailMessage, EmailMultiAlternatives, mail_admins, mail_managers,
    send_mail, send_mass_mail,
)
from django.core.mail.backends import console, dummy, filebased, locmem, smtp
from django.core.mail.message import BadHeaderError
from django.test import SimpleTestCase, override_settings
from django.utils.encoding import force_bytes, force_text
from django.utils.six import PY3, StringIO, binary_type
from django.utils.translation import ugettext_lazy

if PY3:
    from email.utils import parseaddr
    from email import message_from_bytes, message_from_binary_file
else:
    from email.Utils import parseaddr
    from email import (message_from_string as message_from_bytes,
        message_from_file as message_from_binary_file)


class HeadersCheckMixin(object):

    def assertMessageHasHeaders(self, message, headers):
        """
        Check that :param message: has all :param headers: headers.

        :param message: can be an instance of an email.Message subclass or a
        string with the contents of an email message.
        :param headers: should be a set of (header-name, header-value) tuples.
        """
        if isinstance(message, binary_type):
            message = message_from_bytes(message)
        msg_headers = set(message.items())
        self.assertTrue(headers.issubset(msg_headers), msg='Message is missing '
                        'the following headers: %s' % (headers - msg_headers),)


class MailTests(HeadersCheckMixin, SimpleTestCase):
    """
    Non-backend specific tests.
    """

    def test_ascii(self):
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'])
        message = email.message()
        self.assertEqual(message['Subject'], 'Subject')
        self.assertEqual(message.get_payload(), 'Content')
        self.assertEqual(message['From'], 'from@example.com')
        self.assertEqual(message['To'], 'to@example.com')

    def test_multiple_recipients(self):
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com', 'other@example.com'])
        message = email.message()
        self.assertEqual(message['Subject'], 'Subject')
        self.assertEqual(message.get_payload(), 'Content')
        self.assertEqual(message['From'], 'from@example.com')
        self.assertEqual(message['To'], 'to@example.com, other@example.com')

    def test_cc(self):
        """Regression test for #7722"""
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'], cc=['cc@example.com'])
        message = email.message()
        self.assertEqual(message['Cc'], 'cc@example.com')
        self.assertEqual(email.recipients(), ['to@example.com', 'cc@example.com'])

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

    def test_reply_to(self):
        email = EmailMessage(
            'Subject', 'Content', 'from@example.com', ['to@example.com'],
            reply_to=['reply_to@example.com'],
        )
        message = email.message()
        self.assertEqual(message['Reply-To'], 'reply_to@example.com')

        email = EmailMessage(
            'Subject', 'Content', 'from@example.com', ['to@example.com'],
            reply_to=['reply_to1@example.com', 'reply_to2@example.com']
        )
        message = email.message()
        self.assertEqual(message['Reply-To'], 'reply_to1@example.com, reply_to2@example.com')

    def test_recipients_as_tuple(self):
        email = EmailMessage('Subject', 'Content', 'from@example.com', ('to@example.com', 'other@example.com'), cc=('cc@example.com', 'cc.other@example.com'), bcc=('bcc@example.com',))
        message = email.message()
        self.assertEqual(message['Cc'], 'cc@example.com, cc.other@example.com')
        self.assertEqual(email.recipients(), ['to@example.com', 'other@example.com', 'cc@example.com', 'cc.other@example.com', 'bcc@example.com'])

    def test_recipients_as_string(self):
        with self.assertRaisesMessage(TypeError, '"to" argument must be a list or tuple'):
            EmailMessage(to='foo@example.com')
        with self.assertRaisesMessage(TypeError, '"cc" argument must be a list or tuple'):
            EmailMessage(cc='foo@example.com')
        with self.assertRaisesMessage(TypeError, '"bcc" argument must be a list or tuple'):
            EmailMessage(bcc='foo@example.com')
        with self.assertRaisesMessage(TypeError, '"reply_to" argument must be a list or tuple'):
            EmailMessage(reply_to='reply_to@example.com')

    def test_header_injection(self):
        email = EmailMessage('Subject\nInjection Test', 'Content', 'from@example.com', ['to@example.com'])
        self.assertRaises(BadHeaderError, email.message)
        email = EmailMessage(ugettext_lazy('Subject\nInjection Test'), 'Content', 'from@example.com', ['to@example.com'])
        self.assertRaises(BadHeaderError, email.message)

    def test_space_continuation(self):
        """
        Test for space continuation character in long (ASCII) subject headers (#7747)
        """
        email = EmailMessage('Long subject lines that get wrapped should contain a space continuation character to get expected behavior in Outlook and Thunderbird', 'Content', 'from@example.com', ['to@example.com'])
        message = email.message()
        # Note that in Python 3, maximum line length has increased from 76 to 78
        self.assertEqual(message['Subject'].encode(), b'Long subject lines that get wrapped should contain a space continuation\n character to get expected behavior in Outlook and Thunderbird')

    def test_message_header_overrides(self):
        """
        Specifying dates or message-ids in the extra headers overrides the
        default values (#9233)
        """
        headers = {"date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        email = EmailMessage('subject', 'content', 'from@example.com', ['to@example.com'], headers=headers)

        self.assertMessageHasHeaders(email.message(), {
            ('Content-Transfer-Encoding', '7bit'),
            ('Content-Type', 'text/plain; charset="utf-8"'),
            ('From', 'from@example.com'),
            ('MIME-Version', '1.0'),
            ('Message-ID', 'foo'),
            ('Subject', 'subject'),
            ('To', 'to@example.com'),
            ('date', 'Fri, 09 Nov 2001 01:08:47 -0000'),
        })

    def test_from_header(self):
        """
        Make sure we can manually set the From header (#9214)
        """
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        message = email.message()
        self.assertEqual(message['From'], 'from@example.com')

    def test_to_header(self):
        """
        Make sure we can manually set the To header (#17444)
        """
        email = EmailMessage('Subject', 'Content', 'bounce@example.com',
                             ['list-subscriber@example.com', 'list-subscriber2@example.com'],
                             headers={'To': 'mailing-list@example.com'})
        message = email.message()
        self.assertEqual(message['To'], 'mailing-list@example.com')
        self.assertEqual(email.to, ['list-subscriber@example.com', 'list-subscriber2@example.com'])

        # If we don't set the To header manually, it should default to the `to` argument to the constructor
        email = EmailMessage('Subject', 'Content', 'bounce@example.com',
                             ['list-subscriber@example.com', 'list-subscriber2@example.com'])
        message = email.message()
        self.assertEqual(message['To'], 'list-subscriber@example.com, list-subscriber2@example.com')
        self.assertEqual(email.to, ['list-subscriber@example.com', 'list-subscriber2@example.com'])

    def test_reply_to_header(self):
        """
        Specifying 'Reply-To' in headers should override reply_to.
        """
        email = EmailMessage(
            'Subject', 'Content', 'bounce@example.com', ['to@example.com'],
            reply_to=['foo@example.com'], headers={'Reply-To': 'override@example.com'},
        )
        message = email.message()
        self.assertEqual(message['Reply-To'], 'override@example.com')

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

    def test_unicode_address_header(self):
        """
        Regression for #11144 - When a to/from/cc header contains unicode,
        make sure the email addresses are parsed correctly (especially with
        regards to commas)
        """
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['"Firstname Sürname" <to@example.com>', 'other@example.com'])
        self.assertEqual(email.message()['To'], '=?utf-8?q?Firstname_S=C3=BCrname?= <to@example.com>, other@example.com')
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['"Sürname, Firstname" <to@example.com>', 'other@example.com'])
        self.assertEqual(email.message()['To'], '=?utf-8?q?S=C3=BCrname=2C_Firstname?= <to@example.com>, other@example.com')

    def test_unicode_headers(self):
        email = EmailMessage("Gżegżółka", "Content", "from@example.com", ["to@example.com"],
                             headers={"Sender": '"Firstname Sürname" <sender@example.com>',
                                      "Comments": 'My Sürname is non-ASCII'})
        message = email.message()
        self.assertEqual(message['Subject'], '=?utf-8?b?R8W8ZWfFvMOzxYJrYQ==?=')
        self.assertEqual(message['Sender'], '=?utf-8?q?Firstname_S=C3=BCrname?= <sender@example.com>')
        self.assertEqual(message['Comments'], '=?utf-8?q?My_S=C3=BCrname_is_non-ASCII?=')

    def test_safe_mime_multipart(self):
        """
        Make sure headers can be set with a different encoding than utf-8 in
        SafeMIMEMultipart as well
        """
        headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        from_email, to = 'from@example.com', '"Sürname, Firstname" <to@example.com>'
        text_content = 'This is an important message.'
        html_content = '<p>This is an <strong>important</strong> message.</p>'
        msg = EmailMultiAlternatives('Message from Firstname Sürname', text_content, from_email, [to], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.encoding = 'iso-8859-1'
        self.assertEqual(msg.message()['To'], '=?iso-8859-1?q?S=FCrname=2C_Firstname?= <to@example.com>')
        self.assertEqual(msg.message()['Subject'], '=?iso-8859-1?q?Message_from_Firstname_S=FCrname?=')

    def test_encoding(self):
        """
        Regression for #12791 - Encode body correctly with other encodings
        than utf-8
        """
        email = EmailMessage('Subject', 'Firstname Sürname is a great guy.', 'from@example.com', ['other@example.com'])
        email.encoding = 'iso-8859-1'
        message = email.message()
        self.assertMessageHasHeaders(message, {
            ('MIME-Version', '1.0'),
            ('Content-Type', 'text/plain; charset="iso-8859-1"'),
            ('Content-Transfer-Encoding', 'quoted-printable'),
            ('Subject', 'Subject'),
            ('From', 'from@example.com'),
            ('To', 'other@example.com')})
        self.assertEqual(message.get_payload(), 'Firstname S=FCrname is a great guy.')

        # Make sure MIME attachments also works correctly with other encodings than utf-8
        text_content = 'Firstname Sürname is a great guy.'
        html_content = '<p>Firstname Sürname is a <strong>great</strong> guy.</p>'
        msg = EmailMultiAlternatives('Subject', text_content, 'from@example.com', ['to@example.com'])
        msg.encoding = 'iso-8859-1'
        msg.attach_alternative(html_content, "text/html")
        payload0 = msg.message().get_payload(0)
        self.assertMessageHasHeaders(payload0, {
            ('MIME-Version', '1.0'),
            ('Content-Type', 'text/plain; charset="iso-8859-1"'),
            ('Content-Transfer-Encoding', 'quoted-printable')})
        self.assertTrue(payload0.as_bytes().endswith(b'\n\nFirstname S=FCrname is a great guy.'))
        payload1 = msg.message().get_payload(1)
        self.assertMessageHasHeaders(payload1, {
            ('MIME-Version', '1.0'),
            ('Content-Type', 'text/html; charset="iso-8859-1"'),
            ('Content-Transfer-Encoding', 'quoted-printable')})
        self.assertTrue(payload1.as_bytes().endswith(b'\n\n<p>Firstname S=FCrname is a <strong>great</strong> guy.</p>'))

    def test_attachments(self):
        """Regression test for #9367"""
        headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        subject, from_email, to = 'hello', 'from@example.com', 'to@example.com'
        text_content = 'This is an important message.'
        html_content = '<p>This is an <strong>important</strong> message.</p>'
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.attach("an attachment.pdf", b"%PDF-1.4.%...", mimetype="application/pdf")
        msg_bytes = msg.message().as_bytes()
        message = message_from_bytes(msg_bytes)
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_content_type(), 'multipart/mixed')
        self.assertEqual(message.get_default_type(), 'text/plain')
        payload = message.get_payload()
        self.assertEqual(payload[0].get_content_type(), 'multipart/alternative')
        self.assertEqual(payload[1].get_content_type(), 'application/pdf')

    def test_non_ascii_attachment_filename(self):
        """Regression test for #14964"""
        headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
        subject, from_email, to = 'hello', 'from@example.com', 'to@example.com'
        content = 'This is the message.'
        msg = EmailMessage(subject, content, from_email, [to], headers=headers)
        # Unicode in file name
        msg.attach("une pièce jointe.pdf", b"%PDF-1.4.%...", mimetype="application/pdf")
        msg_bytes = msg.message().as_bytes()
        message = message_from_bytes(msg_bytes)
        payload = message.get_payload()
        self.assertEqual(payload[1].get_filename(), 'une pièce jointe.pdf')

    def test_dummy_backend(self):
        """
        Make sure that dummy backends returns correct number of sent messages
        """
        connection = dummy.EmailBackend()
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        self.assertEqual(connection.send_messages([email, email, email]), 3)

    def test_arbitrary_keyword(self):
        """
        Make sure that get_connection() accepts arbitrary keyword that might be
        used with custom backends.
        """
        c = mail.get_connection(fail_silently=True, foo='bar')
        self.assertTrue(c.fail_silently)

    def test_custom_backend(self):
        """Test custom backend defined in this suite."""
        conn = mail.get_connection('mail.custombackend.EmailBackend')
        self.assertTrue(hasattr(conn, 'test_outbox'))
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        conn.send_messages([email])
        self.assertEqual(len(conn.test_outbox), 1)

    def test_backend_arg(self):
        """Test backend argument of mail.get_connection()"""
        self.assertIsInstance(mail.get_connection('django.core.mail.backends.smtp.EmailBackend'), smtp.EmailBackend)
        self.assertIsInstance(mail.get_connection('django.core.mail.backends.locmem.EmailBackend'), locmem.EmailBackend)
        self.assertIsInstance(mail.get_connection('django.core.mail.backends.dummy.EmailBackend'), dummy.EmailBackend)
        self.assertIsInstance(mail.get_connection('django.core.mail.backends.console.EmailBackend'), console.EmailBackend)
        tmp_dir = tempfile.mkdtemp()
        try:
            self.assertIsInstance(mail.get_connection('django.core.mail.backends.filebased.EmailBackend', file_path=tmp_dir), filebased.EmailBackend)
        finally:
            shutil.rmtree(tmp_dir)
        self.assertIsInstance(mail.get_connection(), locmem.EmailBackend)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ADMINS=[('nobody', 'nobody@example.com')],
        MANAGERS=[('nobody', 'nobody@example.com')])
    def test_connection_arg(self):
        """Test connection argument to send_mail(), et. al."""
        mail.outbox = []

        # Send using non-default connection
        connection = mail.get_connection('mail.custombackend.EmailBackend')
        send_mail('Subject', 'Content', 'from@example.com', ['to@example.com'], connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, 'Subject')

        connection = mail.get_connection('mail.custombackend.EmailBackend')
        send_mass_mail([
            ('Subject1', 'Content1', 'from1@example.com', ['to1@example.com']),
            ('Subject2', 'Content2', 'from2@example.com', ['to2@example.com']),
        ], connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 2)
        self.assertEqual(connection.test_outbox[0].subject, 'Subject1')
        self.assertEqual(connection.test_outbox[1].subject, 'Subject2')

        connection = mail.get_connection('mail.custombackend.EmailBackend')
        mail_admins('Admin message', 'Content', connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, '[Django] Admin message')

        connection = mail.get_connection('mail.custombackend.EmailBackend')
        mail_managers('Manager message', 'Content', connection=connection)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(connection.test_outbox), 1)
        self.assertEqual(connection.test_outbox[0].subject, '[Django] Manager message')

    def test_dont_mangle_from_in_body(self):
        # Regression for #13433 - Make sure that EmailMessage doesn't mangle
        # 'From ' in message body.
        email = EmailMessage('Subject', 'From the future', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        self.assertNotIn(b'>From the future', email.message().as_bytes())

    def test_dont_base64_encode(self):
        # Ticket #3472
        # Shouldn't use Base64 encoding at all
        msg = EmailMessage('Subject', 'UTF-8 encoded body', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        self.assertNotIn(b'Content-Transfer-Encoding: base64', msg.message().as_bytes())

        # Ticket #11212
        # Shouldn't use quoted printable, should detect it can represent content with 7 bit data
        msg = EmailMessage('Subject', 'Body with only ASCII characters.', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        s = msg.message().as_bytes()
        self.assertNotIn(b'Content-Transfer-Encoding: quoted-printable', s)
        self.assertIn(b'Content-Transfer-Encoding: 7bit', s)

        # Shouldn't use quoted printable, should detect it can represent content with 8 bit data
        msg = EmailMessage('Subject', 'Body with latin characters: àáä.', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        s = msg.message().as_bytes()
        self.assertNotIn(b'Content-Transfer-Encoding: quoted-printable', s)
        self.assertIn(b'Content-Transfer-Encoding: 8bit', s)

        msg = EmailMessage('Subject', 'Body with non latin characters: А Б В Г Д Е Ж Ѕ З И І К Л М Н О П.', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        s = msg.message().as_bytes()
        self.assertNotIn(b'Content-Transfer-Encoding: quoted-printable', s)
        self.assertIn(b'Content-Transfer-Encoding: 8bit', s)

    def test_dont_base64_encode_message_rfc822(self):
        # Ticket #18967
        # Shouldn't use base64 encoding for a child EmailMessage attachment.
        # Create a child message first
        child_msg = EmailMessage('Child Subject', 'Some body of child message', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        child_s = child_msg.message().as_string()

        # Now create a parent
        parent_msg = EmailMessage('Parent Subject', 'Some parent body', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})

        # Attach to parent as a string
        parent_msg.attach(content=child_s, mimetype='message/rfc822')
        parent_s = parent_msg.message().as_string()

        # Verify that the child message header is not base64 encoded
        self.assertIn(str('Child Subject'), parent_s)

        # Feature test: try attaching email.Message object directly to the mail.
        parent_msg = EmailMessage('Parent Subject', 'Some parent body', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        parent_msg.attach(content=child_msg.message(), mimetype='message/rfc822')
        parent_s = parent_msg.message().as_string()

        # Verify that the child message header is not base64 encoded
        self.assertIn(str('Child Subject'), parent_s)

        # Feature test: try attaching Django's EmailMessage object directly to the mail.
        parent_msg = EmailMessage('Parent Subject', 'Some parent body', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        parent_msg.attach(content=child_msg, mimetype='message/rfc822')
        parent_s = parent_msg.message().as_string()

        # Verify that the child message header is not base64 encoded
        self.assertIn(str('Child Subject'), parent_s)


class PythonGlobalState(SimpleTestCase):
    """
    Tests for #12422 -- Django smarts (#2472/#11212) with charset of utf-8 text
    parts shouldn't pollute global email Python package charset registry when
    django.mail.message is imported.
    """

    def test_utf8(self):
        txt = MIMEText('UTF-8 encoded body', 'plain', 'utf-8')
        self.assertIn('Content-Transfer-Encoding: base64', txt.as_string())

    def test_7bit(self):
        txt = MIMEText('Body with only ASCII characters.', 'plain', 'utf-8')
        self.assertIn('Content-Transfer-Encoding: base64', txt.as_string())

    def test_8bit_latin(self):
        txt = MIMEText('Body with latin characters: àáä.', 'plain', 'utf-8')
        self.assertIn(str('Content-Transfer-Encoding: base64'), txt.as_string())

    def test_8bit_non_latin(self):
        txt = MIMEText('Body with non latin characters: А Б В Г Д Е Ж Ѕ З И І К Л М Н О П.', 'plain', 'utf-8')
        self.assertIn(str('Content-Transfer-Encoding: base64'), txt.as_string())


class BaseEmailBackendTests(HeadersCheckMixin, object):
    email_backend = None

    def setUp(self):
        self.settings_override = override_settings(EMAIL_BACKEND=self.email_backend)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()

    def assertStartsWith(self, first, second):
        if not first.startswith(second):
            self.longMessage = True
            self.assertEqual(first[:len(second)], second, "First string doesn't start with the second.")

    def get_mailbox_content(self):
        raise NotImplementedError('subclasses of BaseEmailBackendTests must provide a get_mailbox_content() method')

    def flush_mailbox(self):
        raise NotImplementedError('subclasses of BaseEmailBackendTests may require a flush_mailbox() method')

    def get_the_message(self):
        mailbox = self.get_mailbox_content()
        self.assertEqual(len(mailbox), 1,
            "Expected exactly one message, got %d.\n%r" % (len(mailbox), [
                m.as_string() for m in mailbox]))
        return mailbox[0]

    def test_send(self):
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'])
        num_sent = mail.get_connection().send_messages([email])
        self.assertEqual(num_sent, 1)
        message = self.get_the_message()
        self.assertEqual(message["subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content")
        self.assertEqual(message["from"], "from@example.com")
        self.assertEqual(message.get_all("to"), ["to@example.com"])

    def test_send_unicode(self):
        email = EmailMessage('Chère maman', 'Je t\'aime très fort', 'from@example.com', ['to@example.com'])
        num_sent = mail.get_connection().send_messages([email])
        self.assertEqual(num_sent, 1)
        message = self.get_the_message()
        self.assertEqual(message["subject"], '=?utf-8?q?Ch=C3=A8re_maman?=')
        self.assertEqual(force_text(message.get_payload(decode=True)), 'Je t\'aime très fort')

    def test_send_many(self):
        email1 = EmailMessage('Subject', 'Content1', 'from@example.com', ['to@example.com'])
        email2 = EmailMessage('Subject', 'Content2', 'from@example.com', ['to@example.com'])
        num_sent = mail.get_connection().send_messages([email1, email2])
        self.assertEqual(num_sent, 2)
        messages = self.get_mailbox_content()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].get_payload(), "Content1")
        self.assertEqual(messages[1].get_payload(), "Content2")

    def test_send_verbose_name(self):
        email = EmailMessage("Subject", "Content", '"Firstname Sürname" <from@example.com>',
                             ["to@example.com"])
        email.send()
        message = self.get_the_message()
        self.assertEqual(message["subject"], "Subject")
        self.assertEqual(message.get_payload(), "Content")
        self.assertEqual(message["from"], "=?utf-8?q?Firstname_S=C3=BCrname?= <from@example.com>")

    def test_plaintext_send_mail(self):
        """
        Test send_mail without the html_message
        regression test for adding html_message parameter to send_mail()
        """
        send_mail('Subject', 'Content', 'sender@example.com', ['nobody@example.com'])
        message = self.get_the_message()

        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get_all('to'), ['nobody@example.com'])
        self.assertFalse(message.is_multipart())
        self.assertEqual(message.get_payload(), 'Content')
        self.assertEqual(message.get_content_type(), 'text/plain')

    def test_html_send_mail(self):
        """Test html_message argument to send_mail"""
        send_mail('Subject', 'Content', 'sender@example.com', ['nobody@example.com'], html_message='HTML Content')
        message = self.get_the_message()

        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get_all('to'), ['nobody@example.com'])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_payload(), 'Content')
        self.assertEqual(message.get_payload(0).get_content_type(), 'text/plain')
        self.assertEqual(message.get_payload(1).get_payload(), 'HTML Content')
        self.assertEqual(message.get_payload(1).get_content_type(), 'text/html')

    @override_settings(MANAGERS=[('nobody', 'nobody@example.com')])
    def test_html_mail_managers(self):
        """Test html_message argument to mail_managers"""
        mail_managers('Subject', 'Content', html_message='HTML Content')
        message = self.get_the_message()

        self.assertEqual(message.get('subject'), '[Django] Subject')
        self.assertEqual(message.get_all('to'), ['nobody@example.com'])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_payload(), 'Content')
        self.assertEqual(message.get_payload(0).get_content_type(), 'text/plain')
        self.assertEqual(message.get_payload(1).get_payload(), 'HTML Content')
        self.assertEqual(message.get_payload(1).get_content_type(), 'text/html')

    @override_settings(ADMINS=[('nobody', 'nobody@example.com')])
    def test_html_mail_admins(self):
        """Test html_message argument to mail_admins """
        mail_admins('Subject', 'Content', html_message='HTML Content')
        message = self.get_the_message()

        self.assertEqual(message.get('subject'), '[Django] Subject')
        self.assertEqual(message.get_all('to'), ['nobody@example.com'])
        self.assertTrue(message.is_multipart())
        self.assertEqual(len(message.get_payload()), 2)
        self.assertEqual(message.get_payload(0).get_payload(), 'Content')
        self.assertEqual(message.get_payload(0).get_content_type(), 'text/plain')
        self.assertEqual(message.get_payload(1).get_payload(), 'HTML Content')
        self.assertEqual(message.get_payload(1).get_content_type(), 'text/html')

    @override_settings(
        ADMINS=[('nobody', 'nobody+admin@example.com')],
        MANAGERS=[('nobody', 'nobody+manager@example.com')])
    def test_manager_and_admin_mail_prefix(self):
        """
        String prefix + lazy translated subject = bad output
        Regression for #13494
        """
        mail_managers(ugettext_lazy('Subject'), 'Content')
        message = self.get_the_message()
        self.assertEqual(message.get('subject'), '[Django] Subject')

        self.flush_mailbox()
        mail_admins(ugettext_lazy('Subject'), 'Content')
        message = self.get_the_message()
        self.assertEqual(message.get('subject'), '[Django] Subject')

    @override_settings(ADMINS=(), MANAGERS=())
    def test_empty_admins(self):
        """
        Test that mail_admins/mail_managers doesn't connect to the mail server
        if there are no recipients (#9383)
        """
        mail_admins('hi', 'there')
        self.assertEqual(self.get_mailbox_content(), [])
        mail_managers('hi', 'there')
        self.assertEqual(self.get_mailbox_content(), [])

    def test_message_cc_header(self):
        """
        Regression test for #7722
        """
        email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'], cc=['cc@example.com'])
        mail.get_connection().send_messages([email])
        message = self.get_the_message()
        self.assertMessageHasHeaders(message, {
            ('MIME-Version', '1.0'),
            ('Content-Type', 'text/plain; charset="utf-8"'),
            ('Content-Transfer-Encoding', '7bit'),
            ('Subject', 'Subject'),
            ('From', 'from@example.com'),
            ('To', 'to@example.com'),
            ('Cc', 'cc@example.com')})
        self.assertIn('\nDate: ', message.as_string())

    def test_idn_send(self):
        """
        Regression test for #14301
        """
        self.assertTrue(send_mail('Subject', 'Content', 'from@öäü.com', ['to@öäü.com']))
        message = self.get_the_message()
        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get('from'), 'from@xn--4ca9at.com')
        self.assertEqual(message.get('to'), 'to@xn--4ca9at.com')

        self.flush_mailbox()
        m = EmailMessage('Subject', 'Content', 'from@öäü.com',
                     ['to@öäü.com'], cc=['cc@öäü.com'])
        m.send()
        message = self.get_the_message()
        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get('from'), 'from@xn--4ca9at.com')
        self.assertEqual(message.get('to'), 'to@xn--4ca9at.com')
        self.assertEqual(message.get('cc'), 'cc@xn--4ca9at.com')

    def test_recipient_without_domain(self):
        """
        Regression test for #15042
        """
        self.assertTrue(send_mail("Subject", "Content", "tester", ["django"]))
        message = self.get_the_message()
        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get('from'), "tester")
        self.assertEqual(message.get('to'), "django")

    def test_close_connection(self):
        """
        Test that connection can be closed (even when not explicitly opened)
        """
        conn = mail.get_connection(username='', password='')
        try:
            conn.close()
        except Exception as e:
            self.fail("close() unexpectedly raised an exception: %s" % e)

    def test_use_as_contextmanager(self):
        """
        Test that the connection can be used as a contextmanager.
        """
        opened = [False]
        closed = [False]
        conn = mail.get_connection(username='', password='')

        def open():
            opened[0] = True
        conn.open = open

        def close():
            closed[0] = True
        conn.close = close
        with conn as same_conn:
            self.assertTrue(opened[0])
            self.assertIs(same_conn, conn)
            self.assertFalse(closed[0])
        self.assertTrue(closed[0])


class LocmemBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = 'django.core.mail.backends.locmem.EmailBackend'

    def get_mailbox_content(self):
        return [m.message() for m in mail.outbox]

    def flush_mailbox(self):
        mail.outbox = []

    def tearDown(self):
        super(LocmemBackendTests, self).tearDown()
        mail.outbox = []

    def test_locmem_shared_messages(self):
        """
        Make sure that the locmen backend populates the outbox.
        """
        connection = locmem.EmailBackend()
        connection2 = locmem.EmailBackend()
        email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        connection.send_messages([email])
        connection2.send_messages([email])
        self.assertEqual(len(mail.outbox), 2)

    def test_validate_multiline_headers(self):
        # Ticket #18861 - Validate emails when using the locmem backend
        with self.assertRaises(BadHeaderError):
            send_mail('Subject\nMultiline', 'Content', 'from@example.com', ['to@example.com'])


class FileBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = 'django.core.mail.backends.filebased.EmailBackend'

    def setUp(self):
        super(FileBackendTests, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self._settings_override = override_settings(EMAIL_FILE_PATH=self.tmp_dir)
        self._settings_override.enable()

    def tearDown(self):
        self._settings_override.disable()
        super(FileBackendTests, self).tearDown()

    def flush_mailbox(self):
        for filename in os.listdir(self.tmp_dir):
            os.unlink(os.path.join(self.tmp_dir, filename))

    def get_mailbox_content(self):
        messages = []
        for filename in os.listdir(self.tmp_dir):
            with open(os.path.join(self.tmp_dir, filename), 'rb') as fp:
                session = fp.read().split(force_bytes('\n' + ('-' * 79) + '\n', encoding='ascii'))
            messages.extend(message_from_bytes(m) for m in session if m)
        return messages

    def test_file_sessions(self):
        """Make sure opening a connection creates a new file"""
        msg = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
        connection = mail.get_connection()
        connection.send_messages([msg])

        self.assertEqual(len(os.listdir(self.tmp_dir)), 1)
        with open(os.path.join(self.tmp_dir, os.listdir(self.tmp_dir)[0]), 'rb') as fp:
            message = message_from_binary_file(fp)
        self.assertEqual(message.get_content_type(), 'text/plain')
        self.assertEqual(message.get('subject'), 'Subject')
        self.assertEqual(message.get('from'), 'from@example.com')
        self.assertEqual(message.get('to'), 'to@example.com')

        connection2 = mail.get_connection()
        connection2.send_messages([msg])
        self.assertEqual(len(os.listdir(self.tmp_dir)), 2)

        connection.send_messages([msg])
        self.assertEqual(len(os.listdir(self.tmp_dir)), 2)

        msg.connection = mail.get_connection()
        self.assertTrue(connection.open())
        msg.send()
        self.assertEqual(len(os.listdir(self.tmp_dir)), 3)
        msg.send()
        self.assertEqual(len(os.listdir(self.tmp_dir)), 3)

        connection.close()


class ConsoleBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = 'django.core.mail.backends.console.EmailBackend'

    def setUp(self):
        super(ConsoleBackendTests, self).setUp()
        self.__stdout = sys.stdout
        self.stream = sys.stdout = StringIO()

    def tearDown(self):
        del self.stream
        sys.stdout = self.__stdout
        del self.__stdout
        super(ConsoleBackendTests, self).tearDown()

    def flush_mailbox(self):
        self.stream = sys.stdout = StringIO()

    def get_mailbox_content(self):
        messages = self.stream.getvalue().split(str('\n' + ('-' * 79) + '\n'))
        return [message_from_bytes(force_bytes(m)) for m in messages if m]

    def test_console_stream_kwarg(self):
        """
        Test that the console backend can be pointed at an arbitrary stream.
        """
        s = StringIO()
        connection = mail.get_connection('django.core.mail.backends.console.EmailBackend', stream=s)
        send_mail('Subject', 'Content', 'from@example.com', ['to@example.com'], connection=connection)
        message = force_bytes(s.getvalue().split('\n' + ('-' * 79) + '\n')[0])
        self.assertMessageHasHeaders(message, {
            ('MIME-Version', '1.0'),
            ('Content-Type', 'text/plain; charset="utf-8"'),
            ('Content-Transfer-Encoding', '7bit'),
            ('Subject', 'Subject'),
            ('From', 'from@example.com'),
            ('To', 'to@example.com')})
        self.assertIn(b'\nDate: ', message)


class FakeSMTPChannel(smtpd.SMTPChannel):

    def collect_incoming_data(self, data):
        try:
            super(FakeSMTPChannel, self).collect_incoming_data(data)
        except UnicodeDecodeError:
            # ignore decode error in SSL/TLS connection tests as we only care
            # whether the connection attempt was made
            pass


class FakeSMTPServer(smtpd.SMTPServer, threading.Thread):
    """
    Asyncore SMTP server wrapped into a thread. Based on DummyFTPServer from:
    http://svn.python.org/view/python/branches/py3k/Lib/test/test_ftplib.py?revision=86061&view=markup
    """
    channel_class = FakeSMTPChannel

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        # New kwarg added in Python 3.5; default switching to False in 3.6.
        if sys.version_info >= (3, 5):
            kwargs['decode_data'] = True
        smtpd.SMTPServer.__init__(self, *args, **kwargs)
        self._sink = []
        self.active = False
        self.active_lock = threading.Lock()
        self.sink_lock = threading.Lock()

    def process_message(self, peer, mailfrom, rcpttos, data):
        if PY3:
            data = data.encode('utf-8')
        m = message_from_bytes(data)
        maddr = parseaddr(m.get('from'))[1]
        if mailfrom != maddr:
            return "553 '%s' != '%s'" % (mailfrom, maddr)
        with self.sink_lock:
            self._sink.append(m)

    def get_sink(self):
        with self.sink_lock:
            return self._sink[:]

    def flush_sink(self):
        with self.sink_lock:
            self._sink[:] = []

    def start(self):
        assert not self.active
        self.__flag = threading.Event()
        threading.Thread.start(self)
        self.__flag.wait()

    def run(self):
        self.active = True
        self.__flag.set()
        while self.active and asyncore.socket_map:
            with self.active_lock:
                asyncore.loop(timeout=0.1, count=1)
        asyncore.close_all()

    def stop(self):
        if self.active:
            self.active = False
            self.join()


class SMTPBackendTestsBase(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super(SMTPBackendTestsBase, cls).setUpClass()
        cls.server = FakeSMTPServer(('127.0.0.1', 0), None)
        cls._settings_override = override_settings(
            EMAIL_HOST="127.0.0.1",
            EMAIL_PORT=cls.server.socket.getsockname()[1])
        cls._settings_override.enable()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls._settings_override.disable()
        cls.server.stop()
        super(SMTPBackendTestsBase, cls).tearDownClass()


class SMTPBackendTests(BaseEmailBackendTests, SMTPBackendTestsBase):
    email_backend = 'django.core.mail.backends.smtp.EmailBackend'

    def setUp(self):
        super(SMTPBackendTests, self).setUp()
        self.server.flush_sink()

    def tearDown(self):
        self.server.flush_sink()
        super(SMTPBackendTests, self).tearDown()

    def flush_mailbox(self):
        self.server.flush_sink()

    def get_mailbox_content(self):
        return self.server.get_sink()

    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password")
    def test_email_authentication_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.username, 'not empty username')
        self.assertEqual(backend.password, 'not empty password')

    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password")
    def test_email_authentication_override_settings(self):
        backend = smtp.EmailBackend(username='username', password='password')
        self.assertEqual(backend.username, 'username')
        self.assertEqual(backend.password, 'password')

    @override_settings(
        EMAIL_HOST_USER="not empty username",
        EMAIL_HOST_PASSWORD="not empty password")
    def test_email_disabled_authentication(self):
        backend = smtp.EmailBackend(username='', password='')
        self.assertEqual(backend.username, '')
        self.assertEqual(backend.password, '')

    def test_auth_attempted(self):
        """
        Test that opening the backend with non empty username/password tries
        to authenticate against the SMTP server.
        """
        backend = smtp.EmailBackend(
            username='not empty username', password='not empty password')
        try:
            self.assertRaisesMessage(SMTPException,
                'SMTP AUTH extension not supported by server.', backend.open)
        finally:
            backend.close()

    def test_server_open(self):
        """
        Test that open() tells us whether it opened a connection.
        """
        backend = smtp.EmailBackend(username='', password='')
        self.assertFalse(backend.connection)
        opened = backend.open()
        backend.close()
        self.assertTrue(opened)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_tls)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_override_settings(self):
        backend = smtp.EmailBackend(use_tls=False)
        self.assertFalse(backend.use_tls)

    def test_email_tls_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertFalse(backend.use_tls)

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_ssl)

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_override_settings(self):
        backend = smtp.EmailBackend(use_ssl=False)
        self.assertFalse(backend.use_ssl)

    def test_email_ssl_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertFalse(backend.use_ssl)

    @override_settings(EMAIL_SSL_CERTFILE='foo')
    def test_email_ssl_certfile_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_certfile, 'foo')

    @override_settings(EMAIL_SSL_CERTFILE='foo')
    def test_email_ssl_certfile_override_settings(self):
        backend = smtp.EmailBackend(ssl_certfile='bar')
        self.assertEqual(backend.ssl_certfile, 'bar')

    def test_email_ssl_certfile_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_certfile, None)

    @override_settings(EMAIL_SSL_KEYFILE='foo')
    def test_email_ssl_keyfile_use_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_keyfile, 'foo')

    @override_settings(EMAIL_SSL_KEYFILE='foo')
    def test_email_ssl_keyfile_override_settings(self):
        backend = smtp.EmailBackend(ssl_keyfile='bar')
        self.assertEqual(backend.ssl_keyfile, 'bar')

    def test_email_ssl_keyfile_default_disabled(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.ssl_keyfile, None)

    @override_settings(EMAIL_USE_TLS=True)
    def test_email_tls_attempts_starttls(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_tls)
        try:
            self.assertRaisesMessage(SMTPException,
                'STARTTLS extension not supported by server.', backend.open)
        finally:
            backend.close()

    @override_settings(EMAIL_USE_SSL=True)
    def test_email_ssl_attempts_ssl_connection(self):
        backend = smtp.EmailBackend()
        self.assertTrue(backend.use_ssl)
        try:
            self.assertRaises(SSLError, backend.open)
        finally:
            backend.close()

    def test_connection_timeout_default(self):
        """Test that the connection's timeout value is None by default."""
        connection = mail.get_connection('django.core.mail.backends.smtp.EmailBackend')
        self.assertEqual(connection.timeout, None)

    def test_connection_timeout_custom(self):
        """Test that the timeout parameter can be customized."""
        class MyEmailBackend(smtp.EmailBackend):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault('timeout', 42)
                super(MyEmailBackend, self).__init__(*args, **kwargs)

        myemailbackend = MyEmailBackend()
        myemailbackend.open()
        self.assertEqual(myemailbackend.timeout, 42)
        self.assertEqual(myemailbackend.connection.timeout, 42)
        myemailbackend.close()

    @override_settings(EMAIL_TIMEOUT=10)
    def test_email_timeout_override_settings(self):
        backend = smtp.EmailBackend()
        self.assertEqual(backend.timeout, 10)

    def test_email_msg_uses_crlf(self):
        """#23063 -- Test that RFC-compliant messages are sent over SMTP."""
        send = SMTP.send
        try:
            smtp_messages = []

            def mock_send(self, s):
                smtp_messages.append(s)
                return send(self, s)

            SMTP.send = mock_send

            email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'])
            mail.get_connection().send_messages([email])

            # Find the actual message
            msg = None
            for i, m in enumerate(smtp_messages):
                if m[:4] == 'data':
                    msg = smtp_messages[i + 1]
                    break

            self.assertTrue(msg)

            if PY3:
                msg = msg.decode('utf-8')
            # Ensure that the message only contains CRLF and not combinations of CRLF, LF, and CR.
            msg = msg.replace('\r\n', '')
            self.assertNotIn('\r', msg)
            self.assertNotIn('\n', msg)

        finally:
            SMTP.send = send


class SMTPBackendStoppedServerTest(SMTPBackendTestsBase):
    """
    This test requires a separate class, because it shuts down the
    FakeSMTPServer started in setUpClass(). It cannot be restarted
    ("RuntimeError: threads can only be started once").
    """

    def test_server_stopped(self):
        """
        Test that closing the backend while the SMTP server is stopped doesn't
        raise an exception.
        """
        backend = smtp.EmailBackend(username='', password='')
        backend.open()
        self.server.stop()
        try:
            backend.close()
        except Exception as e:
            self.fail("close() unexpectedly raised an exception: %s" % e)
