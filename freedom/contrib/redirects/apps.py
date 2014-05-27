from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class RedirectsConfig(AppConfig):
    name = 'freedom.contrib.redirects'
    verbose_name = _("Redirects")
