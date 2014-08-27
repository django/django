from django.apps import AppConfig
# from django.core import checks
# from django.contrib.secure.check.djangosecure import check_security_middleware

from django.utils.translation import ugettext_lazy as _


class SecureConfig(AppConfig):
    name = 'django.contrib.secure'
    verbose_name = _("Security Checks and Enhancements")

    def ready(self):
        # TODO: register all checks here
        # checks.register(checks.Tags.secure)(check_security_middleware)
        pass
