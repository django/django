from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SessionsConfig(AppConfig):
    name = 'django.contrib.sessions'
    verbose_name = _("Sessions")
