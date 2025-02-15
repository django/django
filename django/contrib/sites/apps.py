from thibaud.apps import AppConfig
from thibaud.contrib.sites.checks import check_site_id
from thibaud.core import checks
from thibaud.db.models.signals import post_migrate
from thibaud.utils.translation import gettext_lazy as _

from .management import create_default_site


class SitesConfig(AppConfig):
    default_auto_field = "thibaud.db.models.AutoField"
    name = "thibaud.contrib.sites"
    verbose_name = _("Sites")

    def ready(self):
        post_migrate.connect(create_default_site, sender=self)
        checks.register(check_site_id, checks.Tags.sites)
