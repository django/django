from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class FlatPagesConfig(AppConfig):
    name = 'freedom.contrib.flatpages'
    verbose_name = _("Flat Pages")
