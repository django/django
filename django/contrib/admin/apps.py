from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class AdminConfig(AppConfig):
    name = 'django.contrib.admin'
    verbose_name = _("administration")

    def ready(self):
        self.module.autodiscover()
