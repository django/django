from freedom.apps import AppConfig
from freedom.core import checks
from freedom.contrib.admin.checks import check_admin_app
from freedom.utils.translation import ugettext_lazy as _


class SimpleAdminConfig(AppConfig):
    """Simple AppConfig which does not do automatic discovery."""

    name = 'freedom.contrib.admin'
    verbose_name = _("Administration")

    def ready(self):
        checks.register(checks.Tags.admin)(check_admin_app)


class AdminConfig(SimpleAdminConfig):
    """The default AppConfig for admin which does autodiscovery."""

    def ready(self):
        super(AdminConfig, self).ready()
        self.module.autodiscover()
