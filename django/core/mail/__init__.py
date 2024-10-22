import logging
import smtplib
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.core.mail.exceptions import EmailNotSentException
from django.http import HttpRequest
from django.template import loader
from django.utils.translation import gettext_lazy as _

from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.internal.flows.login_by_code import compare_code
from allauth.account.internal.stagekit import clear_login
from allauth.account.models import EmailAddress, EmailConfirmationMixin
from allauth.core import context

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_CODE_SESSION_KEY = "account_email_verification_code"
EMAIL_VERIFICATION_CODE_TIMEOUT = 60 * 60  # 1 hour

class EmailVerificationModel(EmailConfirmationMixin):
    def __init__(self, email_address: EmailAddress, key: Optional[str] = None):
        self.email_address = email_address
        if not key:
            key = request_email_verification_code(
                context.request, user=email_address.user, email=email_address.email
            )
        self.key = key

    @classmethod
    def create(cls, email_address: EmailAddress):
        return EmailVerificationModel(email_address)

    @classmethod
    def from_key(cls, key):
        verification, _ = get_pending_verification(context.request, peek=True)
        if not verification or not compare_code(actual=key, expected=verification.key):
            return None
        return verification

    def key_expired(self):
        return datetime.now() > self.created_at + datetime.timedelta(seconds=EMAIL_VERIFICATION_CODE_TIMEOUT)

def clear_state(request):
    request.session.pop(EMAIL_VERIFICATION_CODE_SESSION_KEY, None)
    clear_login(request)

def request_email_verification_code(
    request: HttpRequest,
    user,
    email: str,
) -> str:
    code = ""
    pending_verification = {
        "at": time.time(),
        "failed_attempts": 0,
        "email": email,
    }
    pretend = user is None
    if not pretend:
        adapter = get_adapter()
        code = adapter.generate_email_verification_code()
        assert user._meta.pk
        pending_verification.update(
            {
                "user_id": user._meta.pk.value_to_string(user),
                "email": email,
                "code": code,
                "created_at": datetime.now().timestamp(),
            }
        )
    request.session[EMAIL_VERIFICATION_CODE_SESSION_KEY] = pending_verification
    return code

def get_pending_verification(
    request: HttpRequest, peek: bool = False
) -> Tuple[Optional[EmailVerificationModel], Optional[Dict[str, Any]]]:
    if peek:
        data = request.session.get(EMAIL_VERIFICATION_CODE_SESSION_KEY)
    else:
        data = request.session.pop(EMAIL_VERIFICATION_CODE_SESSION_KEY, None)
    if not data:
        clear_state(request)
        return None, None
    if time.time() - data["at"] >= app_settings.EMAIL_VERIFICATION_BY_CODE_TIMEOUT:
        clear_state(request)
        return None, None
    if user_id_str := data.get("user_id"):
        user_id = get_user_model()._meta.pk.to_python(user_id_str)  # type: ignore[union-attr]
        user = get_user_model().objects.get(pk=user_id)
        email = data["email"]
        try:
            email_address = EmailAddress.objects.get_for_user(user, email)
        except EmailAddress.DoesNotExist:
            email_address = EmailAddress(user=user, email=email)
        verification = EmailVerificationModel(email_address, key=data["code"])
    else:
        verification = None
    return verification, data

def record_invalid_attempt(
    request: HttpRequest, pending_verification: Dict[str, Any]
) -> bool:
    n = pending_verification["failed_attempts"]
    n += 1
    pending_verification["failed_attempts"] = n
    if n >= app_settings.EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS:
        clear_state(request)
        return False
    else:
        request.session[EMAIL_VERIFICATION_CODE_SESSION_KEY] = pending_verification
        return True

def send_email(
    subject,
    message,
    recipient_list,
    from_email=None,
    html_message=None,
    fail_silently=False,
    connection=None,
):
    """
    Sends an email using the provided parameters.
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    connection = connection or get_connection()

    try:
        mail = EmailMultiAlternatives(subject, message, from_email, recipient_list, connection=connection)
        if html_message:
            mail.attach_alternative(html_message, "text/html")
        mail.send()
        logger.info("Email sent successfully to %s", recipient_list)
    except EmailNotSentException as e:
        logger.error("Failed to send email: %s", e)
        if not fail_silently:
            raise

def send_email_template(template_name, context, recipient_list, from_email=None, fail_silently=False, connection=None):
    """
    Sends an email using a Django template.
    """
    template = loader.get_template(template_name)
    html_message = template.render(context)
    subject = context.get("subject", "")
    message = context.get("message", "")
    send_email(subject, message, recipient_list, from_email, html_message, fail_silently, connection)

def send_email_with_attachments(
    subject,
    message,
    recipient_list,
    from_email=None,
    attachments=None,
    fail_silently=False,
    connection=None,
):
    """
    Sends an email with attachments.
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    connection = connection or get_connection()

    try:
        mail = EmailMessage(subject, message, from_email, recipient_list, connection=connection)
        if attachments:
            for attachment in attachments:
                mail.attach_file(*attachment)
        mail.send()
        logger.info("Email sent successfully to %s with attachments", recipient_list)
    except EmailNotSentException as e:
        logger.error("Failed to send email: %s", e)
        if not fail_silently:
            raise
        