from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SiteMapsConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "django.contrib.sitemaps"
    verbose_name = _("Site Maps")
