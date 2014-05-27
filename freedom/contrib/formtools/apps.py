from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class FormToolsConfig(AppConfig):
    name = 'freedom.contrib.formtools'
    verbose_name = _("Form Tools")
