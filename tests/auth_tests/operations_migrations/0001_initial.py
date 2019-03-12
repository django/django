from django.db import migrations, models


def assert_minimal_user_contenttype_created(apps, schema_editor):
    """We check that operations can use the created  right after the CreateModel operaiont."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    try:
        ContentType.objects.get_by_natural_key("auth_tests", "minimaluser")
    except ContentType.DoesNotExist:
        raise AssertionError("The auth_tests.MinialUser ContentType should have been created.")


def assert_minimal_user_permissions_are_created(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    content_type = ContentType.objects.get_by_natural_key("auth_tests", "minimaluser")
    assert Permission.objects.filter(content_type=content_type).exists()


class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            'MinimalUser',
            [
                ('id', models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RunPython(assert_minimal_user_contenttype_created, migrations.RunPython.noop),
        migrations.RunPython(assert_minimal_user_permissions_are_created, migrations.RunPython.noop),
    ]

    dependencies = [
        # TODO(arthurio): Update to latest
        ("auth", "0011_update_proxy_permissions"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
