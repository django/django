from django.db import migrations


def assert_renamedfoo_contenttype_not_cached(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    db = schema_editor.connection.alias
    try:
        content_type = ContentType.objects.db_manager(db).get_by_natural_key('contenttypes_tests', 'renamedfoo')
    except ContentType.DoesNotExist:
        pass
    else:
        if not ContentType.objects.db_manager(db).filter(app_label='contenttypes_tests', model='renamedfoo').exists():
            raise AssertionError('The contenttypes_tests.RenamedFoo ContentType should not be cached.')
        elif content_type.model != 'renamedfoo':
            raise AssertionError(
                "The cached contenttypes_tests.RenamedFoo ContentType should have "
                "its model set to 'renamedfoo'."
            )


def assert_foo_contenttype_renamed(apps, schema_editor):
    """We check that operations can use the renamed ContentType right after the RenameModel operation."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    db = schema_editor.connection.alias
    if not ContentType.objects.db_manager(db).filter(app_label="contenttypes_tests", model__endswith="foo").exists():
        # Some tests check the behavior when the content type for Foo doesn't exist
        return

    try:
        # If there is any ContentType for the Foo model at this point, it should be called renamedinfo
        ContentType.objects.db_manager(db).get_by_natural_key("contenttypes_tests", "renamedfoo")
    except ContentType.DoesNotExist:
        raise AssertionError(
            "The contenttypes_tests.Foo ContentType should have been renamed "
            "RenamedFoo."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes_tests', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel('Foo', 'RenamedFoo'),
        migrations.RunPython(assert_renamedfoo_contenttype_not_cached, migrations.RunPython.noop),
        migrations.RunPython(assert_foo_contenttype_renamed, migrations.RunPython.noop),
        migrations.RenameModel('RenamedFoo', 'RenamedTwiceFoo'),
    ]
