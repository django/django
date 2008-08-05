# coding: utf-8
r"""
# Tests for the django.core.mail.

>>> from django.core.mail import EmailMessage
>>> from django.utils.translation import ugettext_lazy

# Test normal ascii character case:

>>> email = EmailMessage('Subject', 'Content', 'from@example.com', ['to@example.com'])
>>> message = email.message()
>>> message['Subject']
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
>>> message['Subject']
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

"""
