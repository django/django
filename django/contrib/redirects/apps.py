from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class RedirectsConfig(AppConfig):
    name = 'django.contrib.redirects'
    verbose_name = _("Redirects")
