# Use this module for e-mailing.

from django.conf import settings
from email.MIMEText import MIMEText
from email.Header import Header
import smtplib, rfc822
import socket
import time
import random

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

def send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=settings.EMAIL_HOST_USER, auth_password=settings.EMAIL_HOST_PASSWORD):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.
    """
    return send_mass_mail([[subject, message, from_email, recipient_list]], fail_silently, auth_user, auth_password)

def send_mass_mail(datatuple, fail_silently=False, auth_user=settings.EMAIL_HOST_USER, auth_password=settings.EMAIL_HOST_PASSWORD):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), sends
    each message to each recipient list. Returns the number of e-mails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    """
    try:
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        if auth_user and auth_password:
            server.login(auth_user, auth_password)
    except:
        if fail_silently:
            return
        raise
    num_sent = 0
    for subject, message, from_email, recipient_list in datatuple:
        if not recipient_list:
            continue
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        msg = SafeMIMEText(message, 'plain', settings.DEFAULT_CHARSET)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ', '.join(recipient_list)
        msg['Date'] = rfc822.formatdate()
        try:
            random_bits = str(random.getrandbits(64))
        except AttributeError: # Python 2.3 doesn't have random.getrandbits().
            random_bits = ''.join([random.choice('1234567890') for i in range(19)])
        msg['Message-ID'] = "<%d.%s@%s>" % (time.time(), random_bits, DNS_NAME)
        try:
            server.sendmail(from_email, recipient_list, msg.as_string())
            num_sent += 1
        except:
            if not fail_silently:
                raise
    try:
        server.quit()
    except:
        if fail_silently:
            return
        raise
    return num_sent

def mail_admins(subject, message, fail_silently=False):
    "Sends a message to the admins, as defined by the ADMINS setting."
    send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, message, settings.SERVER_EMAIL, [a[1] for a in settings.ADMINS], fail_silently)

def mail_managers(subject, message, fail_silently=False):
    "Sends a message to the managers, as defined by the MANAGERS setting."
    send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, message, settings.SERVER_EMAIL, [a[1] for a in settings.MANAGERS], fail_silently)
