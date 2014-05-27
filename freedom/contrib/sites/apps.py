from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class SitesConfig(AppConfig):
    name = 'freedom.contrib.sites'
    verbose_name = _("Sites")
