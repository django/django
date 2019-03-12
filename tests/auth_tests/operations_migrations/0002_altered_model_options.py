from django.db import migrations


def assert_minimal_user_default_permissions_updated(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    try:
        content_type = ContentType.objects.get_by_natural_key(
            "auth_tests", "minimaluser"
        )
    except ContentType.DoesNotExist:
        pass
    else:
        minimal_user_permissions_queryset = Permission.objects.filter(
            content_type=content_type, name__endswith="minimal user"
        )
        if minimal_user_permissions_queryset.exists():
            raise AssertionError(
                "The default permissions for MinimalUser should have been renamed with MiniUser"
            )


def assert_mini_user_default_permissions_updated(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    try:
        content_type = ContentType.objects.get_by_natural_key(
            "auth_tests", "minimaluser"
        )
    except ContentType.DoesNotExist:
        pass
    else:
        mini_user_permissions_queryset = Permission.objects.filter(
            content_type=content_type, name__endswith="mini user"
        )
        if mini_user_permissions_queryset.exists():
            raise AssertionError(
                "The default permissions for MinimalUser should have been reverted to MinimalUser"
            )


def assert_has_6_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    try:
        content_type = ContentType.objects.get_by_natural_key(
            "auth_tests", "minimaluser"
        )
    except ContentType.DoesNotExist:
        pass
    else:
        minimal_user_permissions_queryset = Permission.objects.filter(
            content_type=content_type,
        )
        # add + view + change + delete ("removed" permission) + test + eat == 6
        print("COUNT", minimal_user_permissions_queryset.count())
        print([(p.codename, p.name) for p in minimal_user_permissions_queryset])
        if minimal_user_permissions_queryset.count() != 6:
            raise AssertionError(
                "MinimalUser should have 6 permissions"
            )


def assert_eat_permission_name_is(name):

    def check(apps, schema_editor):
        ContentType = apps.get_model("contenttypes", "ContentType")
        Permission = apps.get_model("auth", "Permission")
        try:
            content_type = ContentType.objects.get_by_natural_key(
                "auth_tests", "minimaluser"
            )
        except ContentType.DoesNotExist:
            pass
        else:
            eat_permission = Permission.objects.get(
                content_type=content_type,
                codename="eat",
            )

            if eat_permission.name != name:
                raise AssertionError(
                    "Eat permission's name should be \"%s\"" % name
                )

    return check


class Migration(migrations.Migration):

    operations = [
        migrations.RunPython(
            migrations.RunPython.noop, assert_mini_user_default_permissions_updated
        ),
        migrations.AlterModelOptions(
            name="MinimalUser", options={"verbose_name": "mini user"}
        ),
        migrations.RunPython(
            assert_minimal_user_default_permissions_updated, migrations.RunPython.noop
        ),
        migrations.RunPython(
            migrations.RunPython.noop, assert_has_6_permissions
        ),
        migrations.AlterModelOptions(
            name="MinimalUser",
            options={
                "default_permissions": ("add", "view", "change", "test"),
                "permissions": (("eat", "Eat pizzas"),)
            },
        ),
        migrations.RunPython(
            assert_has_6_permissions, assert_eat_permission_name_is("Eat pizzas")
        ),
        migrations.AlterModelOptions(
            name="MinimalUser",
            options={
                "permissions": (("eat", "Eat croissants"),)
            },
        ),
        migrations.RunPython(
            assert_eat_permission_name_is("Eat croissants"), migrations.RunPython.noop
        ),
    ]

    dependencies = [("auth_tests", "0001_initial")]
