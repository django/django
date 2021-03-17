from django.apps import AppConfig
from django.contrib.contenttypes.checks import (
    check_generic_foreign_keys, check_model_name_lengths,
)
from django.core import checks
from django.db.migrations.operations import (
    CreateModel, DeleteModel, RenameModel,
)
from django.db.models.signals import post_migrate, post_operation
from django.utils.translation import gettext_lazy as _

from .management import (
    create_contenttypes, inject_create_contenttypes,
    inject_delete_contenttypes, inject_rename_contenttypes,
)


class ContentTypesConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'django.contrib.contenttypes'
    verbose_name = _("Content Types")

    def ready(self):
        post_operation.connect(inject_create_contenttypes, sender=CreateModel)
        post_operation.connect(inject_rename_contenttypes, sender=RenameModel)
        post_operation.connect(inject_delete_contenttypes, sender=DeleteModel)
        post_migrate.connect(create_contenttypes)
        checks.register(check_generic_foreign_keys, checks.Tags.models)
        checks.register(check_model_name_lengths, checks.Tags.models)
