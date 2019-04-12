from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HumanizeConfig(AppConfig):
    name = "django.contrib.humanize"
    verbose_name = _("Humanize")
