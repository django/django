from django.apps import AppConfig
from django.contrib.contenttypes.checks import (check_generic_foreign_keys,
    check_generic_relations)
from django.core import checks
from django.utils.translation import ugettext_lazy as _


class ContentTypesConfig(AppConfig):
    name = 'django.contrib.contenttypes'
    verbose_name = _("Content Types")

    def ready(self):
        checks.register(checks.Tags.models)(check_generic_foreign_keys)
        checks.register(checks.Tags.models)(check_generic_relations)
