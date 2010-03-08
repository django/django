# coding: utf-8
r"""
# Tests for the django.core.mail.

>>> from django.conf import settings
>>> from django.core import mail
>>> from django.core.mail import EmailMessage, mail_admins, mail_managers, EmailMultiAlternatives
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
>>> settings.ADMINS = old_admins
>>> settings.MANAGERS = old_managers

# Make sure we can manually set the From header (#9214)

>>> email = EmailMessage('Subject', 'Content', 'bounce@example.com', ['to@example.com'], headers={'From': 'from@example.com'})
>>> message = email.message()
>>> message['From']
'from@example.com'

# Regression for #11144 - When a to/from/cc header contains unicode,
# make sure the email addresses are parsed correctly (especially
# with regards to commas)
>>> email = EmailMessage('Subject', 'Content', 'from@example.com', ['"Firstname Sürname" <to@example.com>','other@example.com'])
>>> email.message()['To']
'=?utf-8?q?Firstname_S=C3=BCrname?= <to@example.com>, other@example.com'

>>> email = EmailMessage('Subject', 'Content', 'from@example.com', ['"Sürname, Firstname" <to@example.com>','other@example.com'])
>>> email.message()['To']
'=?utf-8?q?S=C3=BCrname=2C_Firstname?= <to@example.com>, other@example.com'

# Regression for #6918 - When a header contains unicode,
# make sure headers can be set with a different encoding than utf-8
>>> email = EmailMessage('Message from Firstname Sürname', 'Content', 'from@example.com', ['"Sürname, Firstname" <to@example.com>','other@example.com'])
>>> email.encoding = 'iso-8859-1'
>>> email.message()['To']
'=?iso-8859-1?q?S=FCrname=2C_Firstname?= <to@example.com>, other@example.com'
>>> email.message()['Subject'].encode() == u'=?iso-8859-1?q?Message_from_Firstname_S=FCrname?='
True

# Make sure headers can be set with a different encoding than utf-8 in SafeMIMEMultipart as well
>>> headers = {"Date": "Fri, 09 Nov 2001 01:08:47 -0000", "Message-ID": "foo"}
>>> subject, from_email, to = 'hello', 'from@example.com', '"Sürname, Firstname" <to@example.com>'
>>> text_content = 'This is an important message.'
>>> html_content = '<p>This is an <strong>important</strong> message.</p>'
>>> msg = EmailMultiAlternatives('Message from Firstname Sürname', text_content, from_email, [to], headers=headers)
>>> msg.attach_alternative(html_content, "text/html")
>>> msg.encoding = 'iso-8859-1'
>>> msg.message()['To']
'=?iso-8859-1?q?S=FCrname=2C_Firstname?= <to@example.com>'
>>> msg.message()['Subject'].encode() == u'=?iso-8859-1?q?Message_from_Firstname_S=FCrname?='
True

# Regression for #12791  - Encode body correctly with other encodings than utf-8
>>> email = EmailMessage('Subject', 'Firstname Sürname is a great guy.', 'from@example.com', ['other@example.com'])
>>> email.encoding = 'iso-8859-1'
>>> message = email.message()
>>> message.as_string()
'Content-Type: text/plain; charset="iso-8859-1"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nSubject: Subject\nFrom: from@example.com\nTo: other@example.com\nDate: ...\nMessage-ID: <...>\n\nFirstname S=FCrname is a great guy.'

# Make sure MIME attachments also works correctly with other encodings than utf-8
>>> text_content = 'Firstname Sürname is a great guy.'
>>> html_content = '<p>Firstname Sürname is a <strong>great</strong> guy.</p>'
>>> msg = EmailMultiAlternatives('Subject', text_content, 'from@example.com', ['to@example.com'])
>>> msg.encoding = 'iso-8859-1'
>>> msg.attach_alternative(html_content, "text/html")
>>> msg.message().get_payload(0).as_string()
'Content-Type: text/plain; charset="iso-8859-1"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\n\nFirstname S=FCrname is a great guy.'
>>> msg.message().get_payload(1).as_string()
'Content-Type: text/html; charset="iso-8859-1"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\n\n<p>Firstname S=FCrname is a <strong>great</strong> guy.</p>'

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

"""
