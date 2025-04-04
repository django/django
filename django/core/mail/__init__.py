"""
Tools for sending email.
"""

from django.conf import settings

# Imported for backwards compatibility and for the sake
# of a cleaner namespace. These symbols used to be in
# django/core/mail.py before the introduction of email
# backends and the subsequent reorganization (See #10355)
from django.core.mail.message import (
    DEFAULT_ATTACHMENT_MIME_TYPE,
    BadHeaderError,
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
    SafeMIMEMultipart,
    SafeMIMEText,
    forbid_multi_line_headers,
    make_msgid,
)
from django.core.mail.utils import DNS_NAME, CachedDnsName
from django.utils.module_loading import import_string

__all__ = [
    "CachedDnsName",
    "DNS_NAME",
    "EmailMessage",
    "EmailMultiAlternatives",
    "SafeMIMEText",
    "SafeMIMEMultipart",
    "DEFAULT_ATTACHMENT_MIME_TYPE",
    "make_msgid",
    "BadHeaderError",
    "forbid_multi_line_headers",
    "get_connection",
    "send_mail",
    "send_mass_mail",
    "mail_admins",
    "mail_managers",
    "EmailAlternative",
    "EmailAttachment",
]


def get_connection(backend=None, fail_silently=False, **kwds):
    """Load an email backend and return an instance of it.

    If backend is None (default), use settings.EMAIL_BACKEND.

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    klass = import_string(backend or settings.EMAIL_BACKEND)
    return klass(fail_silently=fail_silently, **kwds)


def send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
    html_message=None,
):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If from_email is None, use the DEFAULT_FROM_EMAIL setting.
    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=fail_silently,
    )
    mail = EmailMultiAlternatives(
        subject, message, from_email, recipient_list, connection=connection
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")

    return mail.send()


def send_mass_mail(
    datatuple, fail_silently=False, auth_user=None, auth_password=None, connection=None
):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), send
    each message to each recipient list. Return the number of emails sent.

    If from_email is None, use the DEFAULT_FROM_EMAIL setting.
    If auth_user and auth_password are set, use them to log in.
    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=fail_silently,
    )
    messages = [
        EmailMessage(subject, message, sender, recipient, connection=connection)
        for subject, message, sender, recipient in datatuple
    ]
    return connection.send_messages(messages)


def _send_server_message(
    *,
    setting_name,
    subject,
    message,
    html_message=None,
    fail_silently=False,
    connection=None,
):
    recipients = getattr(settings, setting_name)
    if not recipients:
        return

    if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in recipients):
        raise ValueError(f"The {setting_name} setting must be a list of 2-tuples.")

    mail = EmailMultiAlternatives(
        subject="%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        body=message,
        from_email=settings.SERVER_EMAIL,
        to=[a[1] for a in recipients],
        connection=connection,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(fail_silently=fail_silently)


def mail_admins(
    subject, message, fail_silently=False, connection=None, html_message=None
):
    """Send a message to the admins, as defined by the ADMINS setting."""
    _send_server_message(
        setting_name="ADMINS",
        subject=subject,
        message=message,
        html_message=html_message,
        fail_silently=fail_silently,
        connection=connection,
    )


def mail_managers(
    subject, message, fail_silently=False, connection=None, html_message=None
):
    """Send a message to the managers, as defined by the MANAGERS setting."""
    _send_server_message(
        setting_name="MANAGERS",
        subject=subject,
        message=message,
        html_message=html_message,
        fail_silently=fail_silently,
        connection=connection,
    )
