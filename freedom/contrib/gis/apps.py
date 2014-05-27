from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class GISConfig(AppConfig):
    name = 'freedom.contrib.gis'
    verbose_name = _("GIS")
