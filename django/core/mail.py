"""
Tools for sending email.
"""

from django.conf import settings
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import formatdate
from email import Charset
import os
import smtplib
import socket
import time
import random

# Don't BASE64-encode UTF-8 messages so that we avoid unwanted attention from
# some spam filters.
Charset.add_charset('utf-8', Charset.SHORTEST, Charset.QP, 'utf-8')

# Cache the hostname, but do it lazily: socket.getfqdn() can take a couple of
# seconds, which slows down the restart of the server.
class CachedDnsName(object):
    def __str__(self):
        return self.get_fqdn()

    def get_fqdn(self):
        if not hasattr(self, '_fqdn'):
            self._fqdn = socket.getfqdn()
        return self._fqdn

DNS_NAME = CachedDnsName()

# Copied from Python standard library and modified to used the cached hostname
# for performance.
def make_msgid(idstring=None):
    """Returns a string suitable for RFC 2822 compliant Message-ID, e.g:

    <20020201195627.33539.96671@nightshade.la.mastaler.com>

    Optional idstring if given is a string used to strengthen the
    uniqueness of the message id.
    """
    timeval = time.time()
    utcdate = time.strftime('%Y%m%d%H%M%S', time.gmtime(timeval))
    pid = os.getpid()
    randint = random.randrange(100000)
    if idstring is None:
        idstring = ''
    else:
        idstring = '.' + idstring
    idhost = DNS_NAME
    msgid = '<%s.%s.%s%s@%s>' % (utcdate, pid, randint, idstring, idhost)
    return msgid

class BadHeaderError(ValueError):
    pass

class SafeMIMEText(MIMEText):
    def __setitem__(self, name, val):
        "Forbids multi-line headers, to prevent header injection."
        if '\n' in val or '\r' in val:
            raise BadHeaderError, "Header values can't contain newlines (got %r for header %r)" % (val, name)
        if name == "Subject":
            val = Header(val, settings.DEFAULT_CHARSET)
        MIMEText.__setitem__(self, name, val)

class SMTPConnection(object):
    """
    A wrapper that manages the SMTP network connection.
    """

    def __init__(self, host=None, port=None, username=None, password=None,
                 fail_silently=False):
        if host is None:
            self.host = settings.EMAIL_HOST
        if port is None:
            self.port = settings.EMAIL_PORT
        if username is None:
        	self.username = settings.EMAIL_HOST_USER
        if password is None:
	        self.password = settings.EMAIL_HOST_PASSWORD
        self.fail_silently = fail_silently
        self.connection = None

    def open(self):
        """
        Ensure we have a connection to the email server. Returns whether or not
        a new connection was required.
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False
        try:
            self.connection = smtplib.SMTP(self.host, self.port)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except:
            if not self.fail_silently:
                raise

    def close(self):
        """Close the connection to the email server."""
        try:
            try:
                self.connection.quit()
            except:
                if self.fail_silently:
                    return
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return
        new_conn_created = self.open()
        if not self.connection:
            # We failed silently on open(). Trying to send would be pointless.
            return
        num_sent = 0
        for message in email_messages:
            sent = self._send(message)
            if sent:
                num_sent += 1
        if new_conn_created:
            self.close()
        return num_sent

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.to:
            return False
        try:
            self.connection.sendmail(email_message.from_email,
                    email_message.to, email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            return False
        return True

class EmailMessage(object):
    """
    A container for email information.
    """
    def __init__(self, subject='', body='', from_email=None, to=None, connection=None):
        self.to = to or []
        if from_email is None:
            self.from_email = settings.DEFAULT_FROM_EMAIL
        else:
            self.from_email = from_email
        self.subject = subject
        self.body = body
        self.connection = connection

    def get_connection(self, fail_silently=False):
        if not self.connection:
            self.connection = SMTPConnection(fail_silently=fail_silently)
        return self.connection

    def message(self):
        msg = SafeMIMEText(self.body, 'plain', settings.DEFAULT_CHARSET)
        msg['Subject'] = self.subject
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to)
        msg['Date'] = formatdate()
        msg['Message-ID'] = make_msgid()
        return msg

    def send(self, fail_silently=False):
        """Send the email message."""
        return self.get_connection(fail_silently).send_messages([self])

def send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    NOTE: This method is deprecated. It exists for backwards compatibility.
    New code should use the EmailMessage class directly.
    """
    connection = SMTPConnection(username=auth_user, password=auth_password,
                                 fail_silently=fail_silently)
    return EmailMessage(subject, message, from_email, recipient_list, connection=connection).send()

def send_mass_mail(datatuple, fail_silently=False, auth_user=None, auth_password=None):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), sends
    each message to each recipient list. Returns the number of e-mails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    NOTE: This method is deprecated. It exists for backwards compatibility.
    New code should use the EmailMessage class directly.
    """
    connection = SMTPConnection(username=auth_user, password=auth_password,
                                 fail_silently=fail_silently)
    messages = [EmailMessage(subject, message, sender, recipient) for subject, message, sender, recipient in datatuple]
    return connection.send_messages(messages)

def mail_admins(subject, message, fail_silently=False):
    "Sends a message to the admins, as defined by the ADMINS setting."
    EmailMessage(settings.EMAIL_SUBJECT_PREFIX + subject, message,
            settings.SERVER_EMAIL, [a[1] for a in
                settings.ADMINS]).send(fail_silently=fail_silently)

def mail_managers(subject, message, fail_silently=False):
    "Sends a message to the managers, as defined by the MANAGERS setting."
    EmailMessage(settings.EMAIL_SUBJECT_PREFIX + subject, message,
            settings.SERVER_EMAIL, [a[1] for a in
                settings.MANAGERS]).send(fail_silently=fail_silently)

