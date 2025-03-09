from django.apps import AppConfig
from django.contrib.staticfiles.checks import check_finders, check_storages
from django.core import checks
from django.utils.translation import gettext_lazy as _


class StaticFilesConfig(AppConfig):
    name = "django.contrib.staticfiles"
    verbose_name = _("Static Files")
    ignore_patterns = ["CVS", ".*", "*~"]

    def ready(self):
        checks.register(check_finders, checks.Tags.staticfiles)
        checks.register(check_storages, checks.Tags.staticfiles)
