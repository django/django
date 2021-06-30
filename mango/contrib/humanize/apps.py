from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class HumanizeConfig(AppConfig):
    name = 'mango.contrib.humanize'
    verbose_name = _("Humanize")
