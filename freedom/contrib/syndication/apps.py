from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class SyndicationConfig(AppConfig):
    name = 'freedom.contrib.syndication'
    verbose_name = _("Syndication")
