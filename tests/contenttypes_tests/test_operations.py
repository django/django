from django.apps.registry import apps
from django.conf import settings
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import migrations, models
from django.test import TransactionTestCase, override_settings
from unittest.mock import patch


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

        with self.assertWarns(RuntimeWarning):
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

        with self.assertWarns(RuntimeWarning):
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

    def test_rename_contenttype_ignores_integrity_error_on_save(self):
        from django.db import IntegrityError

        class DummyContentType:
            DoesNotExist = type("DoesNotExist", (Exception,), {})

            def __init__(self):
                self.model = "foo"

        class DummyManager:
            def __init__(self, instance):
                self._instance = instance

            def db_manager(self, db):
                return self

            def get_by_natural_key(self, app_label, model):
                return self._instance

            def clear_cache(self):
                pass
            def filter(self, **kwargs):
                return self

            def update(self, **kwargs):
                from django.db import IntegrityError

                raise IntegrityError

        class FakeApps:
            def __init__(self, instance):
                self._instance = instance

            def get_model(self, app_label, name):
                DummyContentType.objects = DummyManager(self._instance)
                return DummyContentType

        class DummySchemaEditor:
            connection = type("C", (), {"alias": "default"})()

        instance = DummyContentType()

        def _save(using=None, update_fields=None):
            raise IntegrityError

        instance.save = _save

        op = contenttypes_management.RenameContentType(
            "contenttypes_tests", "foo", "bar"
        )

        with patch(
            "django.contrib.contenttypes.management.router.allow_migrate_model",
            return_value=True,
        ):
            with self.assertWarnsMessage(RuntimeWarning, "Could not rename ContentType"):
                op._rename(FakeApps(instance), DummySchemaEditor(), "foo", "bar")
            self.assertEqual(instance.model, "foo")

    def test_rename_contenttype_warns_on_integrity_error(self):
        from django.db import IntegrityError

        class DummyContentType:
            DoesNotExist = type("DoesNotExist", (Exception,), {})

            def __init__(self):
                self.model = "oldmodel"

        class DummyManager:
            def __init__(self, instance):
                self._instance = instance

            def db_manager(self, db):
                return self

            def get_by_natural_key(self, app_label, model):
                return self._instance

            def clear_cache(self):
                pass

                def filter(self, **kwargs):
                    return self

                def update(self, **kwargs):
                    # Simulate IntegrityError when attempting to update.
                    raise IntegrityError

        class FakeApps:
            def __init__(self, instance):
                self._instance = instance

            def get_model(self, app_label, name):
                DummyContentType.objects = DummyManager(self._instance)
                return DummyContentType

        class DummySchemaEditor:
            connection = type("C", (), {"alias": "default"})()

        instance = DummyContentType()

        def _save(using=None, update_fields=None):
            raise IntegrityError

        instance.save = _save

        op = contenttypes_management.RenameContentType(
            "contenttypes_tests", "oldmodel", "newmodel"
        )

        class FakeState:
            def __init__(self, apps):
                self.apps = apps

            def clear_delayed_apps_cache(self):
                pass

        with patch(
            "django.contrib.contenttypes.management.router.allow_migrate",
            return_value=True,
        ), patch(
            "django.contrib.contenttypes.management.router.allow_migrate_model",
            return_value=True,
        ):
            from_state = FakeState(FakeApps(instance))
            with self.assertWarnsMessage(RuntimeWarning, "Could not rename ContentType"):
                op.database_forwards(
                    "contenttypes_tests",
                    DummySchemaEditor(),
                    from_state,
                    None,
                )
            self.assertEqual(instance.model, "oldmodel")
