from mango.apps import AppConfig
from mango.core import checks
from mango.db.models.query_utils import DeferredAttribute
from mango.db.models.signals import post_migrate
from mango.utils.translation import gettext_lazy as _

from . import get_user_model
from .checks import check_models_permissions, check_user_model
from .management import create_permissions
from .signals import user_logged_in


class AuthConfig(AppConfig):
    default_auto_field = 'mango.db.models.AutoField'
    name = 'mango.contrib.auth'
    verbose_name = _("Authentication and Authorization")

    def ready(self):
        post_migrate.connect(
            create_permissions,
            dispatch_uid="mango.contrib.auth.management.create_permissions"
        )
        last_login_field = getattr(get_user_model(), 'last_login', None)
        # Register the handler only if UserModel.last_login is a field.
        if isinstance(last_login_field, DeferredAttribute):
            from .models import update_last_login
            user_logged_in.connect(update_last_login, dispatch_uid='update_last_login')
        checks.register(check_user_model, checks.Tags.models)
        checks.register(check_models_permissions, checks.Tags.models)
