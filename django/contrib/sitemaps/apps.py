from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SiteMapsConfig(AppConfig):
    name = 'django.contrib.sitemaps'
    verbose_name = _("Site Maps")
