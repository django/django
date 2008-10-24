# coding: utf-8
r"""
# Tests for the django.core.mail.

>>> from django.conf import settings
>>> from django.core import mail
>>> from django.core.mail import EmailMessage, mail_admins, mail_managers
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

"""
