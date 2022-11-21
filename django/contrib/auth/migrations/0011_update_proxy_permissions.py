import sys

from django.core.management.color import color_style
from django.db import IntegrityError, migrations, transaction
from django.db.models import Q

WARNING = """
    A problem arose migrating proxy model permissions for {old} to {new}.

      Permission(s) for {new} already existed.
      Codenames Q: {query}

    Ensure to audit ALL permissions for {old} and {new}.
"""


def update_proxy_model_permissions(apps, schema_editor, reverse=False):
    """
    Update the content_type of proxy model permissions to use the ContentType
    of the proxy model.
    """
    style = color_style()
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    for Model in apps.get_models():
        opts = Model._meta
        if not opts.proxy:
            continue
        proxy_default_permissions_codenames = [
            f"{action}_{opts.model_name}"
            for action in opts.default_permissions
        ]

        permissions_query = Q(codename__in=proxy_default_permissions_codenames)
        for codename, name in opts.permissions:
            permissions_query |= Q(codename=codename, name=name)
        content_type_manager = ContentType.objects.db_manager(alias)
        concrete_content_type = content_type_manager.get_for_model(
            Model, for_concrete_model=True
        )
        proxy_content_type = content_type_manager.get_for_model(
            Model, for_concrete_model=False
        )
        old_content_type = proxy_content_type if reverse else concrete_content_type
        new_content_type = concrete_content_type if reverse else proxy_content_type
        try:
            with transaction.atomic(using=alias):
                Permission.objects.using(alias).filter(
                    permissions_query,
                    content_type=old_content_type,
                ).update(content_type=new_content_type)
        except IntegrityError:
            old = f"{old_content_type.app_label}_{old_content_type.model}"
            new = f"{new_content_type.app_label}_{new_content_type.model}"
            sys.stdout.write(
                style.WARNING(WARNING.format(old=old, new=new, query=permissions_query))
            )


def revert_proxy_model_permissions(apps, schema_editor):
    """
    Update the content_type of proxy model permissions to use the ContentType
    of the concrete model.
    """
    update_proxy_model_permissions(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0010_alter_group_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [
        migrations.RunPython(
            update_proxy_model_permissions, revert_proxy_model_permissions
        ),
    ]
