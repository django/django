from django.db import migrations, models


def assert_foo_contenttype_created(apps, schema_editor):
    """We check that operations can use the created ContentType right after the CreateModel operaiont."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    try:
        ContentType.objects.get_by_natural_key("contenttypes_tests", "foo")
    except ContentType.DoesNotExist:
        raise AssertionError("The contenttypes_tests.Foo ContentType should have been created.")


class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            'Foo',
            [
                ('id', models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RunPython(assert_foo_contenttype_created, migrations.RunPython.noop),
    ]
