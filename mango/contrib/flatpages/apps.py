from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class FlatPagesConfig(AppConfig):
    default_auto_field = 'mango.db.models.AutoField'
    name = 'mango.contrib.flatpages'
    verbose_name = _("Flat Pages")
