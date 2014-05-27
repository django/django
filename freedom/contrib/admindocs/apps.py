from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class AdminDocsConfig(AppConfig):
    name = 'freedom.contrib.admindocs'
    verbose_name = _("Administrative Documentation")
