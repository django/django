from pathlib import Path

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, skipUnlessDBFeature

from .models import ModelA, ModelC


@skipUnlessDBFeature("supports_table_check_constraints")
class ConstraintsTests(TestCase):
    """Check that the constraints allow valid values and reject invalid ones"""

    def test_ModelA_constraint(self):
        ModelA.objects.create(field="valid")
        with self.assertRaises(IntegrityError):
            ModelA.objects.create(field="invalid")

    def test_ModelC_constraint(self):
        ModelC.objects.create(field="valid")
        with self.assertRaises(IntegrityError):
            ModelC.objects.create(field="invalid")


class ConstraintsMigrationsTests(TestCase):
    """Check that migrations correctly generate the constraints"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Clean and recreate migration files for further inspection
        init_file = Path(__file__).parent / "migrations" / "0001_initial.py"
        init_file.unlink(missing_ok=True)
        call_command("makemigrations", verbosity=0)
        cls.migration_content = init_file.read_text()

    def test_ModelA(self):
        # check migration contents
        self.assertTrue(
            "test_constraint_modela" in self.migration_content,
            "Could not find constraint `test_constraint_modela` in migration",
        )

    def test_ModelC(self):
        # check migration contents
        self.assertTrue(
            "test_constraint_modelc" in self.migration_content,
            "Could not find constraint `test_constraint_modelc` in migration",
        )
