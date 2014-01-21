from django.apps import AppConfig
from django.core import checks
from django.contrib.admin.checks import check_admin_app
from django.utils.translation import ugettext_lazy as _


class AdminConfig(AppConfig):
    name = 'django.contrib.admin'
    verbose_name = _("administration")

    def ready(self):
        self.install_checks()
        self.autodiscover()

    def autodiscover(self):
        self.module.autodiscover()

    def install_checks(self):
        checks.register('admin')(check_admin_app)


class PlainAdminConfig(AdminConfig):
    """Subclass of AdminConfig which does not do automatic discovery."""

    def autodiscover(self):
        pass
