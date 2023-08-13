from importlib import import_module
from pathlib import Path

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

apps = [
    "contribute_to_meta.apps.modelsimple",
    "contribute_to_meta.apps.modelwithmeta",
]


@override_settings(INSTALLED_APPS=apps)
@skipUnlessDBFeature("supports_table_check_constraints")
class ConstraintsTests(TransactionTestCase):
    """Check that the constraints allow valid values and reject invalid ones"""

    available_apps = apps

    def _do_test(self, app_qualified_name):
        app_name = app_qualified_name.split(".")[-1]

        # Reset the migrations
        folder = Path(__file__).parent / "apps" / app_name / "migrations"
        migration_path = folder / "0001_initial.py"
        migration_path.unlink(missing_ok=True)

        # Run the migrations
        call_command("makemigrations", app_name, "--verbosity", "0")
        call_command("migrate", app_name, "--verbosity", "0")

        # Check that the constraint behaves as expected
        Model = import_module(app_qualified_name).models.Model
        Model.objects.create(field="valid")
        with self.assertRaises(IntegrityError):
            Model.objects.create(field="invalid")

        # Check that the constraint is present in the migration file
        migration_path = folder / "0001_initial.py"
        content = migration_path.read_text()
        self.assertTrue(
            "models.CheckConstraint" in content, f"No constraint in `{migration_path}`"
        )

    def test_modelsimple(self):
        self._do_test("contribute_to_meta.apps.modelsimple")

    def test_modelwithmeta(self):
        self._do_test("contribute_to_meta.apps.modelwithmeta")
