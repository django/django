from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class AdminDocsConfig(AppConfig):
    name = "thibaud.contrib.admindocs"
    verbose_name = _("Administrative Documentation")
