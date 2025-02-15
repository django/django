from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class SyndicationConfig(AppConfig):
    name = "thibaud.contrib.syndication"
    verbose_name = _("Syndication")
