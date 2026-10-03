from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.db import IntegrityError, models
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

test_apps = [
    "contribute_to_meta.apps.modelsimple",
    "contribute_to_meta.apps.modelwithmeta",
    "contribute_to_meta.apps.modelchoicefield",
]


@override_settings(INSTALLED_APPS=test_apps)
@skipUnlessDBFeature("supports_table_check_constraints")
class ConstraintsTests(TransactionTestCase):
    """Check that the constraints allow valid values and reject invalid ones"""

    available_apps = test_apps

    @property
    def _app_name(self):
        return self._testMethodName.split("_")[1]

    @property
    def _migrations_folder(self):
        return Path(__file__).parent / "apps" / self._app_name / "migrations"

    def _migration_content(self, migration_name):
        return (self._migrations_folder / migration_name).read_text()

    def setUp(self):
        # Reset the migrations
        for m in self._migrations_folder.glob("????_*.py"):
            m.unlink(missing_ok=True)

    def _do_test(self, app_qualified_name):
        # Run the migrations
        call_command("makemigrations", self._app_name, "--verbosity", "0")
        call_command("migrate", self._app_name, "--verbosity", "0")

        # Check that the constraint behaves as expected
        Model = import_module(app_qualified_name).models.Model
        Model.objects.create(field="valid")
        with self.assertRaises(IntegrityError):
            Model.objects.all().update(field="invalid")

        # Check that the constraint is present in the migration file
        m1 = self._migration_content("0001_initial.py")
        self.assertTrue(
            "models.CheckConstraint" in m1, "No constraint in the migration"
        )

    def test_modelsimple(self):
        self._do_test("contribute_to_meta.apps.modelsimple")

    def test_modelwithmeta(self):
        self._do_test("contribute_to_meta.apps.modelwithmeta")

    def test_modelchoicefield(self):
        """Tests the use where constraints are used to enforce valid choices"""

        from contribute_to_meta.apps.modelchoicefield import models as mcf_models

        from .fields import ChoiceField

        # Create a model with a choice field
        mcf_models.Model = type(
            "Model",
            (models.Model,),
            {
                "__module__": "contribute_to_meta.apps.modelchoicefield.models",
                "Meta": type("Meta", (object,), {"constraints": []}),
                "field": ChoiceField(max_length=10, choices=["a", "b", "c"]),
            },
        )

        # Make the initial migration
        call_command("makemigrations", self._app_name, "--verbosity", "0")

        # Change the model's choices
        del apps.get_app_config(self._app_name).models["model"]
        mcf_models.Model = type(
            "Model",
            (models.Model,),
            {
                "__module__": "contribute_to_meta.apps.modelchoicefield.models",
                "Meta": type("Meta", (object,), {"constraints": []}),
                "field": ChoiceField(max_length=10, choices=["d", "e", "f"]),
            },
        )

        # Make the migration for the change
        call_command(
            "makemigrations", self._app_name, "--name", "update", "--verbosity", "0"
        )

        # Check that the constraint is present in the migration file
        m1 = self._migration_content("0001_initial.py")
        m2 = self._migration_content("0002_update.py")
        self.assertTrue(
            'check=models.Q(("field__in", ["a", "b", "c"]))' in m1,
            "No corresponding constraint in first migration",
        )
        self.assertTrue(
            "migrations.RemoveConstraint" in m2,
            "No drop constraint in second migration",
        )
        self.assertTrue(
            'check=models.Q(("field__in", ["d", "e", "f"]))' in m2,
            "No corresponding constraint in second migration",
        )
