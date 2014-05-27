from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class StaticFilesConfig(AppConfig):
    name = 'freedom.contrib.staticfiles'
    verbose_name = _("Static Files")
