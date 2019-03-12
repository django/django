from django.db import migrations


def assert_model_named_mini_user(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    try:
        content_type = ContentType.objects.get_by_natural_key("auth_tests", "miniuser")
    except ContentType.DoesNotExist:
        pass
    else:
        if (
            not Permission.objects.filter(
                content_type=content_type, name__endswith="mini user"
            ).count() == 4
        ):
            raise AssertionError(
                "The default permissions for MiniUser should have been renamed with MiniUser"
            )


def assert_model_named_minimal_user(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    try:
        content_type = ContentType.objects.get_by_natural_key(
            "auth_tests", "minimaluser"
        )
    except ContentType.DoesNotExist:
        pass
    else:
        print(
            Permission.objects.filter(content_type=content_type).values_list(
                "name", flat=True
            )
        )
        if (
            not Permission.objects.filter(
                content_type=content_type, name__endswith="minimal user"
            ).count() == 4
        ):
            raise AssertionError(
                "The default permissions for MinimalUser should have been reverted to MinimalUser"
            )


class Migration(migrations.Migration):

    operations = [
        migrations.RunPython(
            migrations.RunPython.noop, assert_model_named_minimal_user
        ),
        migrations.RenameModel("MinimalUser", "MiniUser"),
        migrations.RunPython(
            assert_model_named_mini_user, assert_model_named_mini_user
        ),
        migrations.RenameModel("MiniUser", "MinimalUser"),
        migrations.RunPython(
            assert_model_named_minimal_user, migrations.RunPython.noop
        ),
    ]

    dependencies = [("auth_tests", "0002_altered_model_options")]
