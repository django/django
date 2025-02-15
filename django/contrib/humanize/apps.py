from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class HumanizeConfig(AppConfig):
    name = "thibaud.contrib.humanize"
    verbose_name = _("Humanize")
