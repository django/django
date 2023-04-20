from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdminDocsConfig(AppConfig):
    name = "django.contrib.admindocs"
    verbose_name = _("Administrative Documentation")
