from thibaud.apps import AppConfig
from thibaud.contrib.staticfiles.checks import check_finders, check_storages
from thibaud.core import checks
from thibaud.utils.translation import gettext_lazy as _


class StaticFilesConfig(AppConfig):
    name = "thibaud.contrib.staticfiles"
    verbose_name = _("Static Files")
    ignore_patterns = ["CVS", ".*", "*~"]

    def ready(self):
        checks.register(check_finders, checks.Tags.staticfiles)
        checks.register(check_storages, checks.Tags.staticfiles)
