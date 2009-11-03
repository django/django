# coding: utf-8

r"""
# Tests for the django.core.mail.

>>> import os
>>> import shutil
>>> import tempfile
>>> from StringIO import StringIO
>>> from django.conf import settings
>>> from django.core import mail
>>> from django.core.mail import EmailMessage, mail_admins, mail_managers, EmailMultiAlternatives
>>> from django.core.mail import send_mail, send_mass_mail
>>> from django.core.mail.backends.base import BaseEmailBackend
>>> from django.core.mail.backends import console, dummy, locmem, filebased, smtp
>>> from django.utils.translation import ugettext_lazy

# Test normal ascii character case:

>>> email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'])
>>> message = email.message()
>>> message['Subject'].encode()
'Subject'
>>> message.get_payload()
'Content'
>>> message['From']
'from@example.com'
>>> message['To']
'to@example.com'

# Test multiple-recipient case

>>> email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com','other@example.com'])
>>> message = email.message()
>>> message['Subject'].encode()
'Subject'
>>> message.get_payload()
'Content'
>>> message['From']
'from@example.com'
>>> message['To']
'to@example.com, other@example.com'

# Test for header injection

>>> email = EmailMessage('Subject\nInjection Test', 'Content', 'from@example.com', ['to@example.com'])
>>> message = email.message()
Traceback (most recent call last):
    ...
BadHeaderError: Header values can't contain newlines (got u'Subject\nInjection Test' for header 'Subject')

>>> email = EmailMessage(ugettext_lazy('Subject\nInjection Test'), 'Content', 'from@example.com', ['to@example.com'])
>>> message = email.message()
Traceback (most recent call last):
    ...
BadHeaderError: Header values can't contain newlines (got u'Subject\nInjection Test' for header 'Subject')

# Test for space continuation character in long (ascii) subject headers (#7747)

>>> email = EmailMessage('Long subject lines that get wrapped should use a space continuation character to get expected behaviour in Outlook and Thunderbird', 'Content', 'from@example.com', ['to@example.com'])
>>> message = email.message()
>>> message.as_string()
'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: Long subject lines that get wrapped should use a space continuation\n character to get expected behaviour in Outlook and Thunderbird\nFrom: from@example.com\nTo: to@example.com\nDate: ...\nMessage-ID: <...>\n\nContent'

# Specifying dates or message-ids in the extra headers overrides the defaul
# values (#9233).

>>> headers = {"date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
>>> email = EmailMessage('subject', 'content', 'from@example.com', ['to@example.com'], headers=headers)
>>> email.message().as_string()
'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: subject\nFrom: from@example.com\nTo: to@example.com\ndate: Fri, 09 Nov 2001 01:08:47 -0000\nMessage-ID: foo\n\ncontent'

# Test that mail_admins/mail_managers doesn't connect to the mail server if there are no recipients (#9383)

>>> old_admins = settings.ADMINS
>>> old_managers = settings.MANAGERS
>>> settings.ADMINS = []
>>> settings.MANAGERS = []
>>> mail.outbox = []
>>> mail_admins('hi','there')
>>> len(mail.outbox)
0
>>> mail.outbox = []
>>> mail_managers('hi','there')
>>> len(mail.outbox)
0
>>> settings.ADMINS = settings.MANAGERS = [('nobody','nobody@example.com')]
>>> mail.outbox = []
>>> mail_admins('hi','there')
>>> len(mail.outbox)
1
>>> mail.outbox = []
>>> mail_managers('hi','there')
>>> len(mail.outbox)
1

# Make sure we can manually set the From header (#9214)

>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> message = email.message()
>>> message['From']
'from@example.com'

# Handle attachments within an multipart/alternative mail correctly (#9367)
# (test is not as precise/clear as it could be w.r.t. email tree structure,
#  but it's good enough.)

>>> headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
>>> subject, from_email, to = 'hello', 'from@example.com', 'to@example.com'
>>> text_content = 'This is an important message.'
>>> html_content = '<p>This is an <strong>important</strong> message.</p>'
>>> msg = EmailMultiAlternatives(subject, text_content, from_email, [to], headers=headers)
>>> msg.attach_alternative(html_content, "text/html")
>>> msg.attach("an attachment.pdf", "%PDF-1.4.%...", mimetype="application/pdf")
>>> print msg.message().as_string()
Content-Type: multipart/mixed; boundary="..."
MIME-Version: 1.0
Subject: hello
From: from@example.com
To: to@example.com
Date: Fri, 09 Nov 2001 01:08:47 -0000
Message-ID: foo
...
Content-Type: multipart/alternative;...
...
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
...
This is an important message.
...
Content-Type: text/html; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
...
<p>This is an <strong>important</strong> message.</p>
...
...
Content-Type: application/pdf
MIME-Version: 1.0
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="an attachment.pdf"
...
JVBERi0xLjQuJS4uLg==
...

# Make sure that the console backend writes to stdout by default
>>> connection = console.EmailBackend()
>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> connection.send_messages([email])
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: Subject
From: from@example.com
To: to@example.com
Date: ...
Message-ID: ...

Content
-------------------------------------------------------------------------------
1

# Test that the console backend can be pointed at an arbitrary stream
>>> s = StringIO()
>>> connection = mail.get_connection('django.core.mail.backends.console', stream=s)
>>> send_mail('Subject', 'Content', 'from@example.com', ['to@example.com'], connection=connection)
1
>>> print s.getvalue()
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: Subject
From: from@example.com
To: to@example.com
Date: ...
Message-ID: ...

Content
-------------------------------------------------------------------------------

# Make sure that dummy backends returns correct number of sent messages
>>> connection = dummy.EmailBackend()
>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> connection.send_messages([email, email, email])
3

# Make sure that locmen backend populates the outbox
>>> mail.outbox = []
>>> connection = locmem.EmailBackend()
>>> email1 = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> email2 = EmailMessage('Subject 2', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> connection.send_messages([email1, email2])
2
>>> len(mail.outbox)
2
>>> mail.outbox[0].subject
'Subject'
>>> mail.outbox[1].subject
'Subject 2'

# Make sure that multiple locmem connections share mail.outbox
>>> mail.outbox = []
>>> connection1 = locmem.EmailBackend()
>>> connection2 = locmem.EmailBackend()
>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> connection1.send_messages([email])
1
>>> connection2.send_messages([email])
1
>>> len(mail.outbox)
2

# Make sure that the file backend write to the right location
>>> tmp_dir = tempfile.mkdtemp()
>>> connection = filebased.EmailBackend(file_path=tmp_dir)
>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> connection.send_messages([email])
1
>>> len(os.listdir(tmp_dir))
1
>>> print open(os.path.join(tmp_dir, os.listdir(tmp_dir)[0])).read()
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: Subject
From: from@example.com
To: to@example.com
Date: ...
Message-ID: ...

Content
-------------------------------------------------------------------------------

>>> connection2 = filebased.EmailBackend(file_path=tmp_dir)
>>> connection2.send_messages([email])
1
>>> len(os.listdir(tmp_dir))
2
>>> connection.send_messages([email])
1
>>> len(os.listdir(tmp_dir))
2
>>> email.connection = filebased.EmailBackend(file_path=tmp_dir)
>>> connection_created = connection.open()
>>> num_sent = email.send()
>>> len(os.listdir(tmp_dir))
3
>>> num_sent = email.send()
>>> len(os.listdir(tmp_dir))
3
>>> connection.close()
>>> shutil.rmtree(tmp_dir)

# Make sure that get_connection() accepts arbitrary keyword that might be
# used with custom backends.
>>> c = mail.get_connection(fail_silently=True, foo='bar')
>>> c.fail_silently
True

# Test custom backend defined in this suite.
>>> conn = mail.get_connection('regressiontests.mail.custombackend')
>>> hasattr(conn, 'test_outbox')
True
>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> conn.send_messages([email])
1
>>> len(conn.test_outbox)
1

# Test backend argument of mail.get_connection()
>>> isinstance(mail.get_connection('django.core.mail.backends.smtp'), smtp.EmailBackend)
True
>>> isinstance(mail.get_connection('django.core.mail.backends.locmem'), locmem.EmailBackend)
True
>>> isinstance(mail.get_connection('django.core.mail.backends.dummy'), dummy.EmailBackend)
True
>>> isinstance(mail.get_connection('django.core.mail.backends.console'), console.EmailBackend)
True
>>> tmp_dir = tempfile.mkdtemp()
>>> isinstance(mail.get_connection('django.core.mail.backends.filebased', file_path=tmp_dir), filebased.EmailBackend)
True
>>> shutil.rmtree(tmp_dir)
>>> isinstance(mail.get_connection(), locmem.EmailBackend)
True

# Test connection argument of send_mail() et al
>>> connection = mail.get_connection('django.core.mail.backends.console')
>>> send_mail('Subject', 'Content', 'from@example.com', ['to@example.com'], connection=connection)
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: Subject
From: from@example.com
To: to@example.com
Date: ...
Message-ID: ...

Content
-------------------------------------------------------------------------------
1

>>> send_mass_mail([
...         ('Subject1', 'Content1', 'from1@example.com', ['to1@example.com']),
...         ('Subject2', 'Content2', 'from2@example.com', ['to2@example.com'])
...     ], connection=connection)
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: Subject1
From: from1@example.com
To: to1@example.com
Date: ...
Message-ID: ...

Content1
-------------------------------------------------------------------------------
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: Subject2
From: from2@example.com
To: to2@example.com
Date: ...
Message-ID: ...

Content2
-------------------------------------------------------------------------------
2

>>> mail_admins('Subject', 'Content', connection=connection)
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: [Django] Subject
From: root@localhost
To: nobody@example.com
Date: ...
Message-ID: ...

Content
-------------------------------------------------------------------------------

>>> mail_managers('Subject', 'Content', connection=connection)
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
Subject: [Django] Subject
From: root@localhost
To: nobody@example.com
Date: ...
Message-ID: ...

Content
-------------------------------------------------------------------------------

>>> settings.ADMINS = old_admins
>>> settings.MANAGERS = old_managers

"""
