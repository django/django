from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactMessage(models.Model):
    """
    Model to store contact form submissions.
    """

    name = models.CharField(_("name"), max_length=200)
    email = models.EmailField(_("email"))
    message = models.TextField(_("message"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        db_table = "django_contact_message"
        verbose_name = _("contact message")
        verbose_name_plural = _("contact messages")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.created_at:%Y-%m-%d %H:%M}"
