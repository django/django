from django.apps import AppConfig
from django.core import checks
from django.contrib.auth.checks import check_user_model

from django.utils.translation import ugettext_lazy as _


class AuthConfig(AppConfig):
    name = 'django.contrib.auth'
    verbose_name = _("Authentication and Authorization")

    def ready(self):
        checks.register(checks.Tags.models)(check_user_model)
