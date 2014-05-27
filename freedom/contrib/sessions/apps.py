from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class SessionsConfig(AppConfig):
    name = 'freedom.contrib.sessions'
    verbose_name = _("Sessions")
