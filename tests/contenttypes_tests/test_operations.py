from django.apps.registry import apps
from django.conf import settings
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection, migrations, models
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase, override_settings


@override_settings(
    MIGRATION_MODULES=dict(
        settings.MIGRATION_MODULES,
        contenttypes_tests="contenttypes_tests.operations_migrations",
    ),
)
class ContentTypeOperationsTests(TransactionTestCase):
    databases = {"default", "other"}
    available_apps = [
        "contenttypes_tests",
        "django.contrib.contenttypes",
    ]

    class TestRouter:
        def db_for_write(self, model, **hints):
            return "default"

    def setUp(self):
        app_config = apps.get_app_config("contenttypes_tests")
        models.signals.post_migrate.connect(
            self.assertOperationsInjected, sender=app_config
        )
        self.addCleanup(
            models.signals.post_migrate.disconnect,
            self.assertOperationsInjected,
            sender=app_config,
        )

    def assertOperationsInjected(self, plan, **kwargs):
        for migration, _backward in plan:
            operations = iter(migration.operations)
            for operation in operations:
                if isinstance(operation, migrations.RenameModel):
                    next_operation = next(operations)
                    self.assertIsInstance(
                        next_operation, contenttypes_management.RenameContentType
                    )
                    self.assertEqual(next_operation.app_label, migration.app_label)
                    self.assertEqual(next_operation.old_model, operation.old_name_lower)
                    self.assertEqual(next_operation.new_model, operation.new_name_lower)

    def test_existing_content_type_rename(self):
        ContentType.objects.create(app_label="contenttypes_tests", model="foo")
        call_command(
            "migrate",
            "contenttypes_tests",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertFalse(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="foo"
            ).exists()
        )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="renamedfoo"
            ).exists()
        )
        call_command(
            "migrate",
            "contenttypes_tests",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="foo"
            ).exists()
        )
        self.assertFalse(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="renamedfoo"
            ).exists()
        )

    @override_settings(DATABASE_ROUTERS=[TestRouter()])
    def test_existing_content_type_rename_other_database(self):
        ContentType.objects.using("other").create(
            app_label="contenttypes_tests", model="foo"
        )
        other_content_types = ContentType.objects.using("other").filter(
            app_label="contenttypes_tests"
        )
        call_command(
            "migrate",
            "contenttypes_tests",
            database="other",
            interactive=False,
            verbosity=0,
        )
        self.assertFalse(other_content_types.filter(model="foo").exists())
        self.assertTrue(other_content_types.filter(model="renamedfoo").exists())
        call_command(
            "migrate",
            "contenttypes_tests",
            "zero",
            database="other",
            interactive=False,
            verbosity=0,
        )
        self.assertTrue(other_content_types.filter(model="foo").exists())
        self.assertFalse(other_content_types.filter(model="renamedfoo").exists())

    def test_missing_content_type_rename_ignore(self):
        call_command(
            "migrate",
            "contenttypes_tests",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertFalse(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="foo"
            ).exists()
        )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="renamedfoo"
            ).exists()
        )
        call_command(
            "migrate",
            "contenttypes_tests",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="foo"
            ).exists()
        )
        self.assertFalse(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="renamedfoo"
            ).exists()
        )

    def test_content_type_rename_conflict(self):
        ContentType.objects.create(app_label="contenttypes_tests", model="foo")
        ContentType.objects.create(app_label="contenttypes_tests", model="renamedfoo")
        msg = (
            "Could not rename content type 'contenttypes_tests.foo' to "
            "'renamedfoo' due to an existing conflicting content type. "
            "Run 'remove_stale_contenttypes' to clean up stale entries."
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            call_command(
                "migrate",
                "contenttypes_tests",
                database="default",
                interactive=False,
                verbosity=0,
            )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="foo"
            ).exists()
        )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="renamedfoo"
            ).exists()
        )
        msg = (
            "Could not rename content type 'contenttypes_tests.renamedfoo' to "
            "'foo' due to an existing conflicting content type. "
            "Run 'remove_stale_contenttypes' to clean up stale entries."
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            call_command(
                "migrate",
                "contenttypes_tests",
                "zero",
                database="default",
                interactive=False,
                verbosity=0,
            )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="foo"
            ).exists()
        )
        self.assertTrue(
            ContentType.objects.filter(
                app_label="contenttypes_tests", model="renamedfoo"
            ).exists()
        )


@override_settings(
    INSTALLED_APPS=[
        "contenttypes_tests.backward_rename_app",
        "django.contrib.contenttypes",
    ],
    MIGRATION_MODULES=dict(
        settings.MIGRATION_MODULES,
        contenttypes="django.contrib.contenttypes.migrations",
    ),
)
class ContentTypeOperationsBackwardsTests(TransactionTestCase):
    available_apps = [
        "contenttypes_tests.backward_rename_app",
        "django.contrib.contenttypes",
    ]

    def setUp(self):
        recorder = MigrationRecorder(connection)
        for name in ["0001_initial", "0002_remove_content_type_name"]:
            recorder.record_applied("contenttypes", name)
            self.addCleanup(recorder.record_unapplied, "contenttypes", name)

    def assertRenameRoundTrip(self):
        ContentType.objects.create(app_label="app_backward_rename", model="foo")
        content_types = ContentType.objects.filter(app_label="app_backward_rename")
        call_command(
            "migrate",
            "app_backward_rename",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertSequenceEqual(
            content_types.values_list("model", flat=True), ["renamedfoo"]
        )
        call_command(
            "migrate",
            "app_backward_rename",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertSequenceEqual(content_types.values_list("model", flat=True), ["foo"])

    def test_content_type_rename_backwards_before_contenttypes(self):
        self.assertRenameRoundTrip()

    @override_settings(
        MIGRATION_MODULES=dict(
            settings.MIGRATION_MODULES,
            app_backward_rename=(
                "contenttypes_tests.backward_rename_app.migrations_contenttypes_0001"
            ),
            contenttypes="django.contrib.contenttypes.migrations",
        ),
    )
    def test_content_type_rename_backwards_before_contenttypes_0002(self):
        self.assertRenameRoundTrip()
