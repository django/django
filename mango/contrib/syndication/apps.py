from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class SyndicationConfig(AppConfig):
    name = 'mango.contrib.syndication'
    verbose_name = _("Syndication")
