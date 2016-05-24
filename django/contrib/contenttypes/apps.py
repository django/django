from django.apps import AppConfig
from django.contrib.contenttypes.checks import check_generic_foreign_keys
from django.core import checks
from django.db.models.signals import post_migrate, pre_migrate
from django.utils.translation import ugettext_lazy as _

from .management import (
    inject_rename_contenttypes_operations, update_contenttypes,
)


class ContentTypesConfig(AppConfig):
    name = 'django.contrib.contenttypes'
    verbose_name = _("Content Types")

    def ready(self):
        pre_migrate.connect(inject_rename_contenttypes_operations, sender=self)
        post_migrate.connect(update_contenttypes)
        checks.register(check_generic_foreign_keys, checks.Tags.models)
