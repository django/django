"""
Tools for sending email.
"""

import warnings

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
from django.utils.deprecation import RemovedInDjango61Warning
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


def get_connection(backend=None, fail_silently=False, *, provider=None, **kwds):
    """Load an email backend and return an instance of it.

    If backend is None (default), use settings.EMAIL_PROVIDERS[provider]["BACKEND"].
    If provider is None as well, use settings.EMAIL_PROVIDERS["default"]["BACKEND"].

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    if backend:
        if provider:
            raise ValueError(
                "backend and provider are mutually exclusive, "
                "so only use either of those arguments."
            )
        klass = import_string(backend)
        return klass(fail_silently=fail_silently, **kwds)

    provider = provider or getattr(settings, "DEFAULT_EMAIL_PROVIDER_ALIAS", "default")
    klass = import_string(settings.EMAIL_PROVIDERS[provider]["BACKEND"])
    return klass(
        fail_silently=fail_silently,
        use_localtime=settings.EMAIL_PROVIDERS[provider]["USE_LOCALTIME"],
        **(settings.EMAIL_PROVIDERS[provider]["OPTIONS"] | kwds),
    )


def send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    fail_silently=False,
    provider=None,
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
    if provider:
        if connection or auth_user or auth_password:
            raise ValueError(
                "provider and connection/auth_user/auth_password are mutually "
                "exclusive, so only use either of those arguments."
            )
        provider_settings = settings.EMAIL_PROVIDERS[provider]
        connection = get_connection(
            backend=provider_settings["BACKEND"],
            fail_silently=fail_silently,
            **provider_settings["OPTIONS"],
        )
    elif connection:
        msg = (
            "The connection argument is deprecated and will be removed in Django 6.2. "
            "Please use provider with an appropriate configuration instead.",
        )
        warnings.warn(msg, RemovedInDjango61Warning, stacklevel=2)
    else:
        connection = get_connection(
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
    datatuple,
    fail_silently=False,
    provider=None,
    auth_user=None,
    auth_password=None,
    connection=None,
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
    if provider:
        if connection or auth_user or auth_password:
            raise ValueError(
                "provider and connection/auth_user/auth_password are mutually "
                "exclusive, so only use either of those arguments."
            )
        provider_settings = settings.EMAIL_PROVIDERS[provider]
        connection = get_connection(
            backend=provider_settings["BACKEND"],
            fail_silently=fail_silently,
            **provider_settings["OPTIONS"],
        )
    elif connection:
        msg = (
            "The connection argument is deprecated and will be removed in Django 6.2. "
            "Please use provider with an appropriate configuration instead.",
        )
        warnings.warn(msg, RemovedInDjango61Warning, stacklevel=2)
    else:
        connection = get_connection(
            username=auth_user,
            password=auth_password,
            fail_silently=fail_silently,
        )
    messages = [
        EmailMessage(subject, message, sender, recipient, connection=connection)
        for subject, message, sender, recipient in datatuple
    ]
    return connection.send_messages(messages)


def mail_admins(
    subject,
    message,
    fail_silently=False,
    provider=None,
    connection=None,
    html_message=None,
):
    """Send a message to the admins, as defined by the ADMINS setting."""
    if not settings.ADMINS:
        return
    if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in settings.ADMINS):
        raise ValueError("The ADMINS setting must be a list of 2-tuples.")
    mail = EmailMultiAlternatives(
        "%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        message,
        settings.SERVER_EMAIL,
        [a[1] for a in settings.ADMINS],
        provider=provider,
        connection=connection,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(fail_silently=fail_silently)


def mail_managers(
    subject,
    message,
    fail_silently=False,
    provider=None,
    connection=None,
    html_message=None,
):
    """Send a message to the managers, as defined by the MANAGERS setting."""
    if not settings.MANAGERS:
        return
    if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in settings.MANAGERS):
        raise ValueError("The MANAGERS setting must be a list of 2-tuples.")
    mail = EmailMultiAlternatives(
        "%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        message,
        settings.SERVER_EMAIL,
        [a[1] for a in settings.MANAGERS],
        provider=provider,
        connection=connection,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(fail_silently=fail_silently)
