from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class HumanizeConfig(AppConfig):
    name = 'freedom.contrib.humanize'
    verbose_name = _("Humanize")
