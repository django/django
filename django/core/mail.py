# Use this module for e-mailing.

from django.conf.settings import DEFAULT_FROM_EMAIL, EMAIL_HOST, EMAIL_SUBJECT_PREFIX, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from email.MIMEText import MIMEText
import smtplib

class BadHeaderError(ValueError):
    pass

class SafeMIMEText(MIMEText):
    def __setitem__(self, name, val):
        "Forbids multi-line headers, to prevent header injection."
        if '\n' in val or '\r' in val:
            raise BadHeaderError, "Header values can't contain newlines (got %r for header %r)" % (val, name)
        MIMEText.__setitem__(self, name, val)

def send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=EMAIL_HOST_USER, auth_password=EMAIL_HOST_PASSWORD):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.
    """
    return send_mass_mail([[subject, message, from_email, recipient_list]], fail_silently, auth_user, auth_password)

def send_mass_mail(datatuple, fail_silently=False, auth_user=EMAIL_HOST_USER, auth_password=EMAIL_HOST_PASSWORD):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), sends
    each message to each recipient list. Returns the number of e-mails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    """
    try:
        server = smtplib.SMTP(EMAIL_HOST)
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
        from_email = from_email or DEFAULT_FROM_EMAIL
        msg = SafeMIMEText(message)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ', '.join(recipient_list)
        server.sendmail(from_email, recipient_list, msg.as_string())
        num_sent += 1
    server.quit()
    return num_sent

def mail_admins(subject, message, fail_silently=False):
    "Sends a message to the admins, as defined by the ADMINS setting."
    from django.conf.settings import ADMINS, SERVER_EMAIL
    send_mail(EMAIL_SUBJECT_PREFIX + subject, message, SERVER_EMAIL, [a[1] for a in ADMINS], fail_silently)

def mail_managers(subject, message, fail_silently=False):
    "Sends a message to the managers, as defined by the MANAGERS setting."
    from django.conf.settings import MANAGERS, SERVER_EMAIL
    send_mail(EMAIL_SUBJECT_PREFIX + subject, message, SERVER_EMAIL, [a[1] for a in MANAGERS], fail_silently)
