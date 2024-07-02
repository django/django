from django.apps.registry import apps
from django.conf import settings
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import migrations, models
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
        "contenttypes_tests.foo",
        "contenttypes_tests.bar",
        "django.contrib.contenttypes",
    ],
)
class MoveContentTypeOperationsTests(TransactionTestCase):
    databases = {"default", "other"}
    available_apps = [
        "contenttypes_tests.bar",
        "contenttypes_tests.foo",
        "django.contrib.contenttypes",
    ]

    class TestRouter:
        def db_for_write(self, model, **hints):
            return "default"

    def setUp(self):
        app_config = apps.get_app_config("bar")
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
                if isinstance(operation, migrations.CreateModel):
                    next_operation = next(operations)
                    self.assertIsInstance(
                        next_operation, contenttypes_management.MoveContentType
                    )
                    self.assertEqual(next_operation.new_app_label, migration.app_label)
                    self.assertEqual(
                        next_operation.old_app_label, operation.options["old_app_label"]
                    )
                    self.assertEqual(next_operation.model_name, operation.name_lower)

    def test_move_model_content_type_change(self):
        ContentType.objects.create(app_label="bar", model="simplebar")
        call_command(
            "migrate",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertFalse(
            ContentType.objects.filter(app_label="bar", model="simplebar").exists()
        )
        self.assertTrue(
            ContentType.objects.filter(app_label="foo", model="simplebar").exists()
        )
        call_command(
            "migrate",
            "bar",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )
        self.assertTrue(
            ContentType.objects.filter(app_label="bar", model="simplebar").exists()
        )
        self.assertFalse(
            ContentType.objects.filter(app_label="foo", model="simplebar").exists()
        )

    @override_settings(DATABASE_ROUTERS=[TestRouter()])
    def test_content_type_move_model_other_database(self):
        ContentType.objects.using("other").create(app_label="bar", model="simplebar")
        other_content_types = ContentType.objects.using("other").filter(
            model="simplebar"
        )
        call_command(
            "migrate",
            database="other",
            interactive=False,
            verbosity=0,
        )
        self.assertFalse(other_content_types.filter(app_label="bar").exists())
        self.assertTrue(other_content_types.filter(app_label="foo").exists())
        call_command(
            "migrate",
            "bar",
            "zero",
            database="other",
            interactive=False,
            verbosity=0,
        )
        self.assertTrue(other_content_types.filter(app_label="bar").exists())
        self.assertFalse(other_content_types.filter(app_label="foo").exists())
