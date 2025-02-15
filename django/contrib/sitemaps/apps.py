from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class SiteMapsConfig(AppConfig):
    default_auto_field = "thibaud.db.models.AutoField"
    name = "thibaud.contrib.sitemaps"
    verbose_name = _("Site Maps")
