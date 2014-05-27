from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class WebDesignConfig(AppConfig):
    name = 'freedom.contrib.webdesign'
    verbose_name = _("Web Design")
