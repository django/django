from django.apps.registry import apps
from django.conf import settings
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connections, migrations, models
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase, override_settings


@override_settings(
    MIGRATION_MODULES=dict(
        settings.MIGRATION_MODULES,
        contenttypes_tests='contenttypes_tests.operations_migrations',
    ),
)
class ContentTypeOperationsTests(TransactionTestCase):
    available_apps = [
        'contenttypes_tests',
        'django.contrib.contenttypes',
    ]

    def setUp(self):
        app_config = apps.get_app_config('contenttypes_tests')
        models.signals.post_migrate.connect(self.assertOperationsInjected, sender=app_config)

    def tearDown(self):
        app_config = apps.get_app_config('contenttypes_tests')
        models.signals.post_migrate.disconnect(self.assertOperationsInjected, sender=app_config)

    def assertOperationsInjected(self, plan, **kwargs):
        for migration, _backward in plan:
            operations = iter(migration.operations)
            for operation in operations:
                if isinstance(operation, migrations.RenameModel):
                    next_operation = next(operations)
                    self.assertIsInstance(next_operation, contenttypes_management.RenameContentType)
                    self.assertEqual(next_operation.app_label, migration.app_label)
                    self.assertEqual(next_operation.old_model, operation.old_name_lower)
                    self.assertEqual(next_operation.new_model, operation.new_name_lower)

    def test_existing_content_type_rename(self):
        ContentType.objects.create(app_label='contenttypes_tests', model='foo')
        call_command('migrate', 'contenttypes_tests', database='default', interactive=False, verbosity=0,)
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
        call_command('migrate', 'contenttypes_tests', 'zero', database='default', interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())

    def test_missing_content_type_rename_ignore(self):
        call_command('migrate', 'contenttypes_tests', database='default', interactive=False, verbosity=0,)
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
        call_command('migrate', 'contenttypes_tests', 'zero', database='default', interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())

    def test_content_type_rename_conflict(self):
        ContentType.objects.create(app_label='contenttypes_tests', model='foo')
        ContentType.objects.create(app_label='contenttypes_tests', model='renamedfoo')
        call_command('migrate', 'contenttypes_tests', database='default', interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
        call_command('migrate', 'contenttypes_tests', 'zero', database='default', interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())


class ContentTypeOperationsMultiDbTests(TransactionTestCase):
    """
    Test RenameContentType operation with multiple databases to ensure
    the content type is saved on the correct database.
    """
    available_apps = [
        'contenttypes_tests',
        'django.contrib.contenttypes',
    ]
    databases = {'default', 'other'}

    def test_rename_content_type_on_other_database(self):
        """
        RenameContentType saves the content type on the correct database
        when using a database alias other than 'default'.
        """
        # Create a content type on the 'other' database
        ct = ContentType.objects.using('other').create(
            app_label='contenttypes_tests',
            model='oldmodel'
        )

        # Create a mock apps registry and schema editor for 'other' database
        project_state = ProjectState()

        # Create the RenameContentType operation
        operation = contenttypes_management.RenameContentType(
            app_label='contenttypes_tests',
            old_model='oldmodel',
            new_model='newmodel'
        )

        # Execute the rename on the 'other' database
        with connections['other'].schema_editor() as schema_editor:
            operation.rename_forward(apps, schema_editor)

        # Verify that the content type was renamed on the 'other' database
        self.assertFalse(
            ContentType.objects.using('other').filter(
                app_label='contenttypes_tests',
                model='oldmodel'
            ).exists()
        )
        self.assertTrue(
            ContentType.objects.using('other').filter(
                app_label='contenttypes_tests',
                model='newmodel'
            ).exists()
        )

        # Verify that no content type was created/modified on the 'default' database
        self.assertFalse(
            ContentType.objects.using('default').filter(
                app_label='contenttypes_tests',
                model='oldmodel'
            ).exists()
        )
        self.assertFalse(
            ContentType.objects.using('default').filter(
                app_label='contenttypes_tests',
                model='newmodel'
            ).exists()
        )

    def test_rename_content_type_backward_on_other_database(self):
        """
        RenameContentType backward operation saves the content type on the
        correct database when using a database alias other than 'default'.
        """
        # Create a content type on the 'other' database
        ct = ContentType.objects.using('other').create(
            app_label='contenttypes_tests',
            model='newmodel'
        )

        # Create the RenameContentType operation
        operation = contenttypes_management.RenameContentType(
            app_label='contenttypes_tests',
            old_model='oldmodel',
            new_model='newmodel'
        )

        # Execute the backward rename on the 'other' database
        with connections['other'].schema_editor() as schema_editor:
            operation.rename_backward(apps, schema_editor)

        # Verify that the content type was renamed back on the 'other' database
        self.assertTrue(
            ContentType.objects.using('other').filter(
                app_label='contenttypes_tests',
                model='oldmodel'
            ).exists()
        )
        self.assertFalse(
            ContentType.objects.using('other').filter(
                app_label='contenttypes_tests',
                model='newmodel'
            ).exists()
        )

        # Verify that no content type was created/modified on the 'default' database
        self.assertFalse(
            ContentType.objects.using('default').filter(
                app_label='contenttypes_tests',
                model='oldmodel'
            ).exists()
        )
        self.assertFalse(
            ContentType.objects.using('default').filter(
                app_label='contenttypes_tests',
                model='newmodel'
            ).exists()
        )
