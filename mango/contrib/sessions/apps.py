from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class SessionsConfig(AppConfig):
    name = 'mango.contrib.sessions'
    verbose_name = _("Sessions")
