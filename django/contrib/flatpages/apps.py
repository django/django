from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class FlatPagesConfig(AppConfig):
    default_auto_field = "thibaud.db.models.AutoField"
    name = "thibaud.contrib.flatpages"
    verbose_name = _("Flat Pages")
