from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class SitesConfig(AppConfig):
    name = 'django.contrib.sites'
    verbose_name = _("Sites")
