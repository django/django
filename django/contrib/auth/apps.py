from django.apps import AppConfig
from django.core import checks
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

from .checks import check_models_permissions, check_user_model
from .management import create_permissions


class AuthConfig(AppConfig):
    name = 'django.contrib.auth'
    verbose_name = _("Authentication and Authorization")

    def ready(self):
        post_migrate.connect(
            create_permissions,
            dispatch_uid="django.contrib.auth.management.create_permissions"
        )
        checks.register(check_user_model, checks.Tags.models)
        checks.register(check_models_permissions, checks.Tags.models)
