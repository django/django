from mango.apps import AppConfig
from mango.contrib.admin.checks import check_admin_app, check_dependencies
from mango.core import checks
from mango.utils.translation import gettext_lazy as _


class SimpleAdminConfig(AppConfig):
    """Simple AppConfig which does not do automatic discovery."""

    default_auto_field = 'mango.db.models.AutoField'
    default_site = 'mango.contrib.admin.sites.AdminSite'
    name = 'mango.contrib.admin'
    verbose_name = _("Administration")

    def ready(self):
        checks.register(check_dependencies, checks.Tags.admin)
        checks.register(check_admin_app, checks.Tags.admin)


class AdminConfig(SimpleAdminConfig):
    """The default AppConfig for admin which does autodiscovery."""

    default = True

    def ready(self):
        super().ready()
        self.module.autodiscover()
