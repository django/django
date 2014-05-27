from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class SiteMapsConfig(AppConfig):
    name = 'freedom.contrib.sitemaps'
    verbose_name = _("Site Maps")
