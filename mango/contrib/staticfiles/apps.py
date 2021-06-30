from mango.apps import AppConfig
from mango.contrib.staticfiles.checks import check_finders
from mango.core import checks
from mango.utils.translation import gettext_lazy as _


class StaticFilesConfig(AppConfig):
    name = 'mango.contrib.staticfiles'
    verbose_name = _("Static Files")
    ignore_patterns = ['CVS', '.*', '*~']

    def ready(self):
        checks.register(check_finders, checks.Tags.staticfiles)
