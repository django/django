from freedom.apps import AppConfig
from freedom.core import checks
from freedom.contrib.auth.checks import check_user_model

from freedom.utils.translation import ugettext_lazy as _


class AuthConfig(AppConfig):
    name = 'freedom.contrib.auth'
    verbose_name = _("Authentication and Authorization")

    def ready(self):
        checks.register(checks.Tags.models)(check_user_model)
