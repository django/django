from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class SessionsConfig(AppConfig):
    name = "thibaud.contrib.sessions"
    verbose_name = _("Sessions")
