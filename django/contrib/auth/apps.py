from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class AuthConfig(AppConfig):
    name = 'django.contrib.auth'
    verbose_name = _("authentication and authorization")
