import unicodedata

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from .models import Device, TryLaterException
from .otp import TOTP, create_otp_key, secret_key_b32
from .utils import create_b64_qrcode, format_uri

UserModel = get_user_model()
EMAIL_KEY_NAME = "mfa_email_key"
TOTP_KEY_NAME = "mfa_totp_key"
EMAIL_TIME_STEP = settings.MFA_EMAIL_TIME_STEP
TOTP_TIME_STEP = settings.TOTP_TIME_STEP
DIGITS = settings.MFA_DIGITS


def _is_otp_verified(submitted_code, key, time_step=30):
    totp = TOTP(secret_key=key, time_step=time_step)
    is_verified = totp.verify(str(submitted_code))
    return is_verified


class FormMixin:
    def _clean_code(self, *, key_name, time_step):
        code = self.cleaned_data["code"]
        totp = str(code).zfill(DIGITS)
        key = self.session[key_name]

        if not _is_otp_verified(totp, key, time_step):
            raise forms.ValidationError(_("Invalid code"), code="invalid_code")
        return totp

    def post_clean(self, *, key_name, time_step, device_name):
        key = self.session[key_name]
        totp_device = Device(
            name=device_name.upper(),
            user=self.user,
            key=key,
            time_step=time_step,
            digits=DIGITS,
        )

        try:
            totp_device.full_clean()
        except forms.ValidationError as ex:
            self.add_error("__all__", ex.messages)
            return

        self.device_instance = totp_device


class TOTPSetupForm(FormMixin, forms.Form):
    code = forms.IntegerField(label=_("TOTP code"), min_value=0)
    qr_code = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = request.user
        self.session = request.session
        self.host = request.get_host()
        self.device_instance = None
        qr_code_field = self.fields.get("qr_code")

        if not self.data:
            qr_code, key = self._create_qr_code()
            self.session[TOTP_KEY_NAME] = key
            qr_code_field.initial = qr_code
        qr_code_field.value = self.data.get("qr_code")

    def clean_code(self):
        return self._clean_code(key_name=TOTP_KEY_NAME, time_step=TOTP_TIME_STEP)

    def _post_clean(self):
        self.post_clean(
            key_name=TOTP_KEY_NAME, time_step=TOTP_TIME_STEP, device_name="TOTP"
        )

    def _create_qr_code(self):
        secret_key = create_otp_key()
        key_b32 = secret_key_b32(secret_key)
        email_field_name = self.user.get_email_field_name()

        qr_code_uri = format_uri(
            account_name=getattr(self.user, email_field_name, None),
            secret_key=key_b32,
            issuer=self.host,
            period=TOTP_TIME_STEP,
            digits=DIGITS,
        )

        qr_code = create_b64_qrcode(qr_code_uri)
        return qr_code, secret_key

    def save(self):
        del self.session[TOTP_KEY_NAME]
        self.device_instance.save()
        return self.device_instance


class EmailSetupForm(FormMixin, forms.Form):
    code = forms.IntegerField(min_value=0)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = request.user
        self.session = request.session
        self.device_instance = None

    def clean_code(self):
        return self._clean_code(key_name=EMAIL_KEY_NAME, time_step=EMAIL_TIME_STEP)

    def _post_clean(self):
        self.post_clean(
            key_name=EMAIL_KEY_NAME,
            time_step=EMAIL_TIME_STEP,
            device_name="EMAIL",
        )

    def save(self):
        del self.session[EMAIL_KEY_NAME]
        self.device_instance.save()
        return self.device_instance


class EmailVerificationForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)

    def __init__(self, request=None, *args, **kwargs):
        self.user = None
        self.session = request.session
        super().__init__(*args, **kwargs)

        if not self.session.get(EMAIL_KEY_NAME):
            key = create_otp_key()
            self.session[EMAIL_KEY_NAME] = create_otp_key()

    def same_email(self, email):
        email_field_name = UserModel.get_email_field_name()
        try:
            user = UserModel._default_manager.get(**{f"{email_field_name}": email})
            self.user = user
        except UserModel.DoesNotExist:
            return False

        email = unicodedata.normalize("NFKC", user.email).casefold()
        submitted_email = unicodedata.normalize("NFKC", email).casefold()
        return email == submitted_email

    def send_email(self):
        from_email = settings.EMAIL_HOST_USER
        email_field_name = self.user.get_email_field_name()
        to = getattr(self.user, email_field_name, None)
        totp = self._generate_totp()
        subject = "One Time Password"
        context = {"otp": totp}
        html_message = render_to_string("mfa/otp_email.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject,
            plain_message,
            from_email,
            [to],
            html_message=html_message,
            fail_silently=False,
        )

    def _generate_totp(self):
        totp = TOTP(**self._device_attrs())
        no_time_steps = totp.get_no_time_steps()
        index = len(no_time_steps) // 2
        otp = totp.generate(msg=no_time_steps[index])
        return otp

    def _device_attrs(self):
        try:
            device = Device.objects.get(user=self.user, name="EMAIL")
            return {
                "secret_key": device.key,
                "time_step": device.time_step,
                "digits": device.digits,
            }
        except Device.DoesNotExist:
            return {
                "secret_key": self.session.get(EMAIL_KEY_NAME),
                "time_step": EMAIL_TIME_STEP,
                "digits": DIGITS,
            }


class MFAVerificationForm(forms.Form):
    code = forms.IntegerField(min_value=0)

    def __init__(self, device=None, *args, **kwargs):
        self.device = device
        super().__init__(*args, **kwargs)

    def clean_code(self):
        totp = self.cleaned_data.get("code")

        try:
            totp = str(totp).zfill(self.device.digits)
            is_verified = self.device.verify(totp)
        except TryLaterException as ex:
            raise forms.ValidationError(_(str(ex)), code=ex.code)
        except AttributeError:
            raise forms.ValidationError(_("Device doesn't exist."), code="no_device")

        if not is_verified:
            raise forms.ValidationError(_("Invalid code"), code="invalid_code")

        return totp


class DeviceDeleteForm(forms.Form):
    confirm = forms.BooleanField()
