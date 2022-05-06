import datetime
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .otp import TOTP

TOTP_TIME_STEP = settings.TOTP_TIME_STEP
DIGITS = settings.MFA_DIGITS


class TryLaterException(Exception):
    code = "try_later"


class DeviceManager(models.Manager):
    def get_devices(self, user):
        return self.model.objects.filter(user=user)


class Device(models.Model):
    class DeviceName(models.TextChoices):
        TOTP = "TOTP", _("TOTP")
        SMS = "SMS", _("SMS")
        EMAIL = "EMAIL", _("EMAIL")

    name = models.CharField(
        _("name"),
        max_length=5,
        choices=DeviceName.choices,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
    )
    initial_time = models.DateTimeField(
        _("initial time"),
        default=datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc),
    )
    key = models.CharField(_("key"), max_length=40)
    digits = models.PositiveSmallIntegerField(_("digits"), default=DIGITS)
    time_step = models.PositiveSmallIntegerField(_("time step"), default=TOTP_TIME_STEP)
    failed_attempts = models.PositiveSmallIntegerField(_("failed attempts"), default=0)
    try_later = models.DateTimeField(_("try later"), auto_now_add=True)
    slug = models.UUIDField(_("slug"), default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = DeviceManager()

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        constraints = [UniqueConstraint(fields=["user", "name"], name="unique_device")]

    def __str__(self):
        return self.name

    def increase_failed_attempts(self):
        self.failed_attempts += 1
        self.save()

    def reset_failed_attempts(self):
        self.failed_attempts = F("failed_attempts") - F("failed_attempts")
        self.save()

    def set_try_later(self):
        try_later = settings.MFA_TRY_LATER
        self.try_later = timezone.now() + datetime.timedelta(seconds=try_later)
        self.save()

    @property
    def can_try_again(self):
        return self.try_later <= timezone.now()

    @property
    def max_attempt_reached(self):
        return self.failed_attempts >= settings.MFA_MAX_ALLOWED_ATTEMPTS

    @property
    def waiting_time(self):
        seconds = (self.try_later - timezone.now()).seconds
        waiting_time = datetime.datetime.fromtimestamp(seconds).strftime("%M:%S")
        return waiting_time

    def pre_verify(self):
        if self.max_attempt_reached and self.can_try_again:
            self.set_try_later()
            self.reset_failed_attempts()
            raise TryLaterException(f"Try again in {self.waiting_time} minutes.")

        if not self.can_try_again:
            raise TryLaterException(f"Try again in {self.waiting_time} minutes.")

    def get_totp(self):
        return TOTP(
            secret_key=self.key,
            time_step=self.time_step,
            digits=self.digits,
            t0=self.initial_time.timestamp(),
        )

    def verify(self, code):
        self.pre_verify()
        totp = self.get_totp()
        is_verified = totp.verify(str(code))

        if not is_verified:
            self.increase_failed_attempts()
        else:
            self.reset_failed_attempts()

        return is_verified
