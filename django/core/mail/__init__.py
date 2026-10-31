"""
Tools for sending email.
"""

from email.headerregistry import Address

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.exceptions import InvalidMailer, MailerDoesNotExist
from django.core.mail.handler import MailersHandler

# Imported for backwards compatibility and for the sake
# of a cleaner namespace. These symbols used to be in
# django/core/mail.py before the introduction of email
# backends and the subsequent reorganization (See #10355)
from django.core.mail.message import (
    DEFAULT_ATTACHMENT_MIME_TYPE,
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
    make_msgid,
)
from django.core.mail.utils import DNS_NAME, CachedDnsName
from django.utils.functional import Promise

__all__ = [
    "InvalidMailer",
    "MailerDoesNotExist",
    "CachedDnsName",
    "DNS_NAME",
    "EmailMessage",
    "EmailMultiAlternatives",
    "DEFAULT_ATTACHMENT_MIME_TYPE",
    "make_msgid",
    "mailers",
    "send_mail",
    "send_mass_mail",
    "mail_admins",
    "mail_managers",
    "EmailAlternative",
    "EmailAttachment",
]


mailers = MailersHandler()


def send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    *,
    html_message=None,
    using=None,
):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If from_email is None, use the DEFAULT_FROM_EMAIL setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    email = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    if html_message:
        email.attach_alternative(html_message, "text/html")
    return email.send(using=using)


def send_mass_mail(
    datatuple,
    *,
    using=None,
):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), send
    each message to each recipient list. Return the number of emails sent.

    If from_email is None, use the DEFAULT_FROM_EMAIL setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    messages = [
        EmailMessage(subject, message, sender, recipient)
        for subject, message, sender, recipient in datatuple
    ]
    mailer = mailers.default if using is None else mailers[using]
    return mailer.send_messages(messages)


def _send_server_message(
    *,
    setting_name,
    subject,
    message,
    html_message=None,
    using=None,
):
    recipients = getattr(settings, setting_name)
    if not recipients:
        return

    if not isinstance(recipients, (list, tuple)) or not all(
        isinstance(address, (str, Promise, Address)) for address in recipients
    ):
        raise ImproperlyConfigured(
            f"The {setting_name} setting must be a list of email address "
            "strings or Address objects."
        )

    mail = EmailMultiAlternatives(
        subject="%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        body=message,
        from_email=settings.SERVER_EMAIL,
        to=recipients,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(using=using)


def mail_admins(
    subject,
    message,
    *,
    html_message=None,
    using=None,
):
    """Send a message to the admins, as defined by the ADMINS setting."""
    _send_server_message(
        setting_name="ADMINS",
        subject=subject,
        message=message,
        html_message=html_message,
        using=using,
    )


def mail_managers(
    subject,
    message,
    *,
    html_message=None,
    using=None,
):
    """Send a message to the managers, as defined by the MANAGERS setting."""
    _send_server_message(
        setting_name="MANAGERS",
        subject=subject,
        message=message,
        html_message=html_message,
        using=using,
    )
