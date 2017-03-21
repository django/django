from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

from .management import create_default_site


class SitesConfig(AppConfig):
    name = 'django.contrib.sites'
    verbose_name = _("Sites")

    def ready(self):
        post_migrate.connect(create_default_site, sender=self)
