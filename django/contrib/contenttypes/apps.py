from django.apps import AppConfig
from django.contrib.contenttypes.checks import check_generic_foreign_keys
from django.core import checks
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy as _

from .management import update_contenttypes


class ContentTypesConfig(AppConfig):
    name = 'django.contrib.contenttypes'
    verbose_name = _("Content Types")

    def ready(self):
        post_migrate.connect(update_contenttypes)
        checks.register(check_generic_foreign_keys, checks.Tags.models)
