from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class AdminDocsConfig(AppConfig):
    name = 'mango.contrib.admindocs'
    verbose_name = _("Administrative Documentation")
