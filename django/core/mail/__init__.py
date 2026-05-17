"""
Tools for sending email.
"""

import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.exceptions import InvalidMailer, MailerDoesNotExist
from django.core.mail.handler import DEFAULT_MAILER_ALIAS, MailersHandler

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
    forbid_multi_line_headers,
    make_msgid,
)
from django.core.mail.utils import DNS_NAME, CachedDnsName
from django.utils.deprecation import (
    RemovedInDjango70Warning,
    deprecate_posargs,
    warn_about_external_use,
)
from django.utils.functional import Promise
from django.utils.module_loading import import_string

from .deprecation import (
    AUTH_ARGS_WARNING,
    CONNECTION_ARG_WARNING,
    FAIL_SILENTLY_ARG_WARNING,
    report_using_incompatibility,
    warn_about_default_mailers_if_needed,
)

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
    "get_connection",
    "send_mail",
    "send_mass_mail",
    "mail_admins",
    "mail_managers",
    "EmailAlternative",
    "EmailAttachment",
    # RemovedInDjango70Warning: When the deprecation ends, remove the last
    # entries.
    "BadHeaderError",
    "SafeMIMEText",
    "SafeMIMEMultipart",
    "forbid_multi_line_headers",
]


mailers = MailersHandler()


# RemovedInDjango70Warning.
@deprecate_posargs(RemovedInDjango70Warning, ["fail_silently"])
def get_connection(backend=None, *, fail_silently=False, **kwds):
    """Load an email backend and return an instance of it.

    If backend is None (default), use settings.EMAIL_BACKEND.

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    msg = (
        "get_connection() is deprecated. See 'Migrating email to mailers' "
        "in Django's documentation for recommended replacements."
    )
    warn_about_external_use(msg, RemovedInDjango70Warning, skip_frames=1)
    warn_about_default_mailers_if_needed()

    if fail_silently:
        kwds["fail_silently"] = fail_silently

    if mailers._is_configured:
        # Support get_connection(**kwargs) from MAILERS["default"].
        if backend is not None:
            raise RuntimeError(
                "get_connection(backend, ...) is not supported with MAILERS."
            )
        return mailers.create_connection(DEFAULT_MAILER_ALIAS, _deprecated_kwargs=kwds)

    klass = import_string(backend or settings.EMAIL_BACKEND)
    return klass(**kwds)


@deprecate_posargs(
    RemovedInDjango70Warning,
    [
        "fail_silently",
        "auth_user",
        "auth_password",
        "connection",
        "html_message",
    ],
)
def send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    *,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
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
    # RemovedInDjango70Warning: change entire implementation to:
    #   email = EmailMultiAlternatives(
    #       subject, message, from_email, recipient_list
    #   )
    #   if html_message:
    #       email.attach_alternative(html_message, "text/html")
    #   return email.send(using=using)
    if fail_silently:
        warn_about_external_use(
            FAIL_SILENTLY_ARG_WARNING, RemovedInDjango70Warning, skip_frames=1
        )
    if auth_user is not None or auth_password is not None:
        warn_about_external_use(
            AUTH_ARGS_WARNING, RemovedInDjango70Warning, skip_frames=1
        )
    if connection is not None:
        warn_about_external_use(
            CONNECTION_ARG_WARNING, RemovedInDjango70Warning, skip_frames=1
        )

    if using is not None:
        report_using_incompatibility(
            connection, fail_silently, auth_user, auth_password
        )
    elif connection is None:
        options = {"fail_silently": fail_silently}
        if auth_user is not None:
            options["username"] = auth_user
        if auth_password is not None:
            options["password"] = auth_password
        connection = get_connection(**options)
    else:
        if fail_silently:
            raise TypeError(
                "fail_silently cannot be used with a connection. "
                "Pass fail_silently to get_connection() instead."
            )
        if auth_user is not None or auth_password is not None:
            raise TypeError(
                "auth_user and auth_password cannot be used with a connection. "
                "Pass auth_user and auth_password to get_connection() instead."
            )
    mail = EmailMultiAlternatives(
        subject, message, from_email, recipient_list, connection=connection
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")

    return mail.send(using=using)


@deprecate_posargs(
    RemovedInDjango70Warning,
    [
        "fail_silently",
        "auth_user",
        "auth_password",
        "connection",
    ],
)
def send_mass_mail(
    datatuple,
    *,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
    using=None,
):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), send
    each message to each recipient list. Return the number of emails sent.

    If from_email is None, use the DEFAULT_FROM_EMAIL setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    # RemovedInDjango70Warning: change entire implementation to:
    #   messages = [...]
    #   mailer = mailers.default if using is None else mailers[using]
    #   return mailer.send_messages(messages)
    if fail_silently:
        warn_about_external_use(
            FAIL_SILENTLY_ARG_WARNING, RemovedInDjango70Warning, skip_frames=1
        )
    if auth_user is not None or auth_password is not None:
        warn_about_external_use(
            AUTH_ARGS_WARNING, RemovedInDjango70Warning, skip_frames=1
        )
    if connection is not None:
        warn_about_external_use(
            CONNECTION_ARG_WARNING, RemovedInDjango70Warning, skip_frames=1
        )

    if using is not None:
        report_using_incompatibility(
            connection, fail_silently, auth_user, auth_password
        )
        connection = mailers[using]
    elif connection is None:
        options = {"fail_silently": fail_silently}
        if auth_user is not None:
            options["username"] = auth_user
        if auth_password is not None:
            options["password"] = auth_password
        connection = get_connection(**options)
    else:
        if fail_silently:
            raise TypeError(
                "fail_silently cannot be used with a connection. "
                "Pass fail_silently to get_connection() instead."
            )
        if auth_user is not None or auth_password is not None:
            raise TypeError(
                "auth_user and auth_password cannot be used with a connection. "
                "Pass auth_user and auth_password to get_connection() instead."
            )
    messages = [
        EmailMessage(subject, message, sender, recipient, connection=connection)
        for subject, message, sender, recipient in datatuple
    ]
    return connection.send_messages(messages)


# RemovedInDjango70Warning: fail_silently and connection args.
def _send_server_message(
    *,
    setting_name,
    subject,
    message,
    html_message=None,
    fail_silently=False,
    connection=None,
    using=None,
):
    # RemovedInDjango70Warning: everything before `recipients = getattr(...)`.
    # skip_frames=2: this helper's caller + its @deprecate_posargs decorator.
    if fail_silently:
        warn_about_external_use(
            FAIL_SILENTLY_ARG_WARNING, RemovedInDjango70Warning, skip_frames=2
        )
    if connection is not None:
        warn_about_external_use(
            CONNECTION_ARG_WARNING, RemovedInDjango70Warning, skip_frames=2
        )

    if using is not None:
        report_using_incompatibility(connection, fail_silently)
    elif connection is not None and fail_silently:
        raise TypeError(
            "fail_silently cannot be used with a connection. "
            "Pass fail_silently to get_connection() instead."
        )
    # ... end of RemovedInDjango70Warning.

    recipients = getattr(settings, setting_name)
    if not recipients:
        return

    # RemovedInDjango70Warning.
    if all(isinstance(a, (list, tuple)) and len(a) == 2 for a in recipients):
        warnings.warn(
            f"Using (name, address) pairs in the {setting_name} setting is deprecated."
            " Replace with a list of email address strings.",
            RemovedInDjango70Warning,
            stacklevel=2,
        )
        recipients = [a[1] for a in recipients]

    if not isinstance(recipients, (list, tuple)) or not all(
        isinstance(address, (str, Promise)) for address in recipients
    ):
        raise ImproperlyConfigured(
            f"The {setting_name} setting must be a list of email address strings."
        )

    mail = EmailMultiAlternatives(
        subject="%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        body=message,
        from_email=settings.SERVER_EMAIL,
        to=recipients,
        connection=connection,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(using=using, fail_silently=fail_silently)


# RemovedInDjango70Warning: fail_silently and connection args.
@deprecate_posargs(
    RemovedInDjango70Warning, ["fail_silently", "connection", "html_message"]
)
def mail_admins(
    subject,
    message,
    *,
    fail_silently=False,
    connection=None,
    html_message=None,
    using=None,
):
    """Send a message to the admins, as defined by the ADMINS setting."""
    _send_server_message(
        setting_name="ADMINS",
        subject=subject,
        message=message,
        html_message=html_message,
        fail_silently=fail_silently,
        connection=connection,
        using=using,
    )


# RemovedInDjango70Warning: fail_silently and connection args.
@deprecate_posargs(
    RemovedInDjango70Warning, ["fail_silently", "connection", "html_message"]
)
def mail_managers(
    subject,
    message,
    *,
    fail_silently=False,
    connection=None,
    html_message=None,
    using=None,
):
    """Send a message to the managers, as defined by the MANAGERS setting."""
    _send_server_message(
        setting_name="MANAGERS",
        subject=subject,
        message=message,
        html_message=html_message,
        fail_silently=fail_silently,
        connection=connection,
        using=using,
    )


# RemovedInDjango70Warning.
_deprecate_on_import = {
    "BadHeaderError": "BadHeaderError is deprecated. Replace with ValueError.",
    "SafeMIMEText": (
        "SafeMIMEText is deprecated. The return value"
        " of EmailMessage.message() is an email.message.EmailMessage."
    ),
    "SafeMIMEMultipart": (
        "SafeMIMEMultipart is deprecated. The return value"
        " of EmailMessage.message() is an email.message.EmailMessage."
    ),
}


# RemovedInDjango70Warning.
def __getattr__(name):
    try:
        msg = _deprecate_on_import[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    else:
        # Issue deprecation warnings at time of import.
        from django.core.mail import message

        warnings.warn(msg, category=RemovedInDjango70Warning)
        return getattr(message, name)
