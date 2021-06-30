from mango.apps import AppConfig
from mango.contrib.sites.checks import check_site_id
from mango.core import checks
from mango.db.models.signals import post_migrate
from mango.utils.translation import gettext_lazy as _

from .management import create_default_site


class SitesConfig(AppConfig):
    default_auto_field = 'mango.db.models.AutoField'
    name = 'mango.contrib.sites'
    verbose_name = _("Sites")

    def ready(self):
        post_migrate.connect(create_default_site, sender=self)
        checks.register(check_site_id, checks.Tags.sites)
