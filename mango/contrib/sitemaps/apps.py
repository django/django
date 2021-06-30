from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class SiteMapsConfig(AppConfig):
    default_auto_field = 'mango.db.models.AutoField'
    name = 'mango.contrib.sitemaps'
    verbose_name = _("Site Maps")
