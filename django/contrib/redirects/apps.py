from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RedirectsConfig(AppConfig):
    name = 'django.contrib.redirects'
    verbose_name = _("Redirects")
