from freedom.apps import AppConfig
from freedom.contrib.contenttypes.checks import check_generic_foreign_keys
from freedom.core import checks
from freedom.utils.translation import ugettext_lazy as _


class ContentTypesConfig(AppConfig):
    name = 'freedom.contrib.contenttypes'
    verbose_name = _("Content Types")

    def ready(self):
        checks.register(checks.Tags.models)(check_generic_foreign_keys)
