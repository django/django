from django.conf import settings
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import models
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase, override_settings


@override_settings(
    MIGRATION_MODULES=dict(
        settings.MIGRATION_MODULES,
        contenttypes="django.contrib.contenttypes.migrations",
        auth="django.contrib.auth.migrations",
        contenttypes_tests="contenttypes_tests.operations_migrations",
    ),
)
class ContentTypeOperationsTests(TransactionTestCase):
    databases = {'default', 'other'}
    available_apps = [
        "django.contrib.contenttypes",
        "contenttypes_tests",
    ]

    class TestRouter:
        def db_for_write(self, model, **hints):
            return 'default'

    def setUp(self):
        # `contenttypes` is one of the apps for which the migrations are skipped in the tests setup.
        # Fake the migrations to record them in the database and have them be part of the migration plan.
        call_command("migrate", "contenttypes", database="default", interactive=False, verbosity=0, fake=True)

        models.signals.post_operation.connect(
            self.assertRenameOperationsInjected,
            sender=contenttypes_management.RenameContentType,
        )
        self.addCleanup(
            models.signals.post_operation.disconnect,
            self.assertRenameOperationsInjected,
            sender=contenttypes_management.RenameContentType,
        )

        models.signals.post_operation.connect(
            self.assertCreateOperationsInjected,
            sender=contenttypes_management.CreateContentType,
        )
        self.addCleanup(
            models.signals.post_operation.disconnect,
            self.assertCreateOperationsInjected,
            sender=contenttypes_management.CreateContentType,
        )

    def assertCreateOperationsInjected(self, operation, migration, from_state, to_state, root_operation, **kwargs):
        self.assertIsInstance(operation, contenttypes_management.CreateContentType)
        self.assertEqual(operation.app_label, migration.app_label)
        self.assertEqual(operation.model, root_operation.name_lower)

    def assertRenameOperationsInjected(self, operation, migration, from_state, to_state, root_operation, **kwargs):
        self.assertIsInstance(operation, contenttypes_management.RenameContentType)
        self.assertEqual(operation.app_label, migration.app_label)
        self.assertEqual(operation.old_model, root_operation.old_name_lower)
        self.assertEqual(operation.new_model, root_operation.new_name_lower)

    def test_content_type_create(self):
        call_command("migrate", "contenttypes_tests", "0001", database="default", interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        call_command("migrate", "contenttypes_tests", "zero", database="default", interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())

    def test_existing_content_type_rename(self):
        call_command("migrate", "contenttypes_tests", database="default", interactive=False, verbosity=0)
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedtwicefoo").exists())
        call_command("migrate", "contenttypes_tests", "zero", database="default", interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedtwicefoo").exists())

    @override_settings(DATABASE_ROUTERS=[TestRouter()])
    def test_existing_content_type_rename_other_database(self):
        ContentType.objects.using('other').create(app_label='contenttypes_tests', model='foo')
        other_content_types = ContentType.objects.using('other').filter(app_label='contenttypes_tests')
        call_command('migrate', 'contenttypes_tests', database='other', interactive=False, verbosity=0)
        self.assertFalse(other_content_types.filter(model='foo').exists())
        self.assertTrue(other_content_types.filter(model='renamedfoo').exists())
        call_command('migrate', 'contenttypes_tests', 'zero', database='other', interactive=False, verbosity=0)
        self.assertTrue(other_content_types.filter(model='foo').exists())
        self.assertFalse(other_content_types.filter(model='renamedfoo').exists())

    def test_missing_content_type_rename_ignore(self):
        ContentType.objects.filter(app_label="contettypes_tests", model="foo").delete()
        call_command("migrate", "contenttypes_tests", database="default", interactive=False, verbosity=0)
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedtwicefoo").exists())
        call_command("migrate", "contenttypes_tests", "zero", database="default", interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedtwicefoo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())

    def test_content_type_rename_conflict(self):
        ContentType.objects.create(app_label="contenttypes_tests", model="foo")
        ContentType.objects.create(app_label="contenttypes_tests", model="renamedfoo")
        ContentType.objects.create(app_label="contenttypes_tests", model="renamedtwicefoo")
        call_command("migrate", "contenttypes_tests", database="default", interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedtwicefoo").exists())
        call_command("migrate", "contenttypes_tests", "zero", database="default", interactive=False, verbosity=0)
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())
        self.assertTrue(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedtwicefoo").exists())


@override_settings(
    MIGRATION_MODULES=dict(
        contenttypes_tests="contenttypes_tests.noop_migrations",
    ),
)
class ContentTypeNotInstalledOperationsTests(TransactionTestCase):
    available_apps = [
        "contenttypes_tests",
    ]

    def setUp(self):
        models.signals.post_operation.connect(
            self.assertOperationsNotInjected,
            sender=contenttypes_management.RenameContentType,
        )
        self.addCleanup(
            models.signals.post_operation.disconnect,
            self.assertOperationsNotInjected,
            sender=contenttypes_management.RenameContentType,
        )
        self.addCleanup(
            call_command,
            "migrate",
            "contenttypes_tests",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )

    def assertOperationsNotInjected(self, operation, migration, from_state, to_state, root_operation, **kwargs):
        raise AssertionError('django.contrib.contenttypes is not registered, this operation shouldn"t be injected.')

    def test_contenttypes_previously_installed(self):
        # Fake having `contenttypes` previously installed but removed from `INSTALLED_APPS`
        record = MigrationRecorder.Migration.objects.create(
            app="contenttypes",
            name="0001_initial",
        )
        # Make sure migration is not considered applied once the test is rolled back.
        self.addCleanup(record.delete)

        call_command("migrate", "contenttypes_tests", database="default", interactive=False, verbosity=0)
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())

    def test_contenttypes_never_installed(self):
        call_command("migrate", "contenttypes_tests", database="default", interactive=False, verbosity=0)
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="foo").exists())
        self.assertFalse(ContentType.objects.filter(app_label="contenttypes_tests", model="renamedfoo").exists())
