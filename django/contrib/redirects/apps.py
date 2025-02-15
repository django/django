from thibaud.apps import AppConfig
from thibaud.utils.translation import gettext_lazy as _


class RedirectsConfig(AppConfig):
    default_auto_field = "thibaud.db.models.AutoField"
    name = "thibaud.contrib.redirects"
    verbose_name = _("Redirects")
