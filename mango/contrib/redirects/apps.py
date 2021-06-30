from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class RedirectsConfig(AppConfig):
    default_auto_field = 'mango.db.models.AutoField'
    name = 'mango.contrib.redirects'
    verbose_name = _("Redirects")
