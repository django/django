import math

from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, connection, migrations, models, transaction
from django.db.migrations.migration import Migration
from django.db.migrations.operations.fields import FieldOperation
from django.db.migrations.state import ModelState, ProjectState
from django.db.models.expressions import Value
from django.db.models.functions import Abs, Pi
from django.db.transaction import atomic
from django.test import (
    SimpleTestCase,
    ignore_warnings,
    override_settings,
    skipIfDBFeature,
    skipUnlessDBFeature,
)
from django.test.utils import CaptureQueriesContext
from django.utils.deprecation import RemovedInDjango51Warning

from .models import FoodManager, FoodQuerySet, UnicodeModel
from .test_base import OperationTestBase


class Mixin:
    pass


class OperationTests(OperationTestBase):
    """
    Tests running the operations and making sure they do what they say they do.
    Each test looks at their state changing, and then their database operation -
    both forwards and backwards.
    """

    def test_create_model(self):
        """
        Tests the CreateModel operation.
        Most other tests use this operation as part of setup, so check failures
        here first.
        """
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
        )
        self.assertEqual(operation.describe(), "Create model Pony")
        self.assertEqual(operation.migration_name_fragment, "pony")
        # Test the state alteration
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        self.assertEqual(new_state.models["test_crmo", "pony"].name, "Pony")
        self.assertEqual(len(new_state.models["test_crmo", "pony"].fields), 2)
        # Test the database alteration
        self.assertTableNotExists("test_crmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableExists("test_crmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["fields", "name"])
        # And default manager not in set
        operation = migrations.CreateModel(
            "Foo", fields=[], managers=[("objects", models.Manager())]
        )
        definition = operation.deconstruct()
        self.assertNotIn("managers", definition[2])

    def test_create_model_with_duplicate_field_name(self):
        with self.assertRaisesMessage(
            ValueError, "Found duplicate value pink in CreateModel fields argument."
        ):
            migrations.CreateModel(
                "Pony",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pink", models.TextField()),
                    ("pink", models.IntegerField(default=1)),
                ],
            )

    def test_create_model_with_duplicate_base(self):
        message = "Found duplicate value test_crmo.pony in CreateModel bases argument."
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    "test_crmo.Pony",
                    "test_crmo.Pony",
                ),
            )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    "test_crmo.Pony",
                    "test_crmo.pony",
                ),
            )
        message = (
            "Found duplicate value migrations.unicodemodel in CreateModel bases "
            "argument."
        )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    UnicodeModel,
                    UnicodeModel,
                ),
            )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    UnicodeModel,
                    "migrations.unicodemodel",
                ),
            )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    UnicodeModel,
                    "migrations.UnicodeModel",
                ),
            )
        message = (
            "Found duplicate value <class 'django.db.models.base.Model'> in "
            "CreateModel bases argument."
        )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    models.Model,
                    models.Model,
                ),
            )
        message = (
            "Found duplicate value <class 'migrations.test_operations.Mixin'> in "
            "CreateModel bases argument."
        )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(
                    Mixin,
                    Mixin,
                ),
            )

    def test_create_model_with_duplicate_manager_name(self):
        with self.assertRaisesMessage(
            ValueError,
            "Found duplicate value objects in CreateModel managers argument.",
        ):
            migrations.CreateModel(
                "Pony",
                fields=[],
                managers=[
                    ("objects", models.Manager()),
                    ("objects", models.Manager()),
                ],
            )

    def test_create_model_with_unique_after(self):
        """
        Tests the CreateModel operation directly followed by an
        AlterUniqueTogether (bug #22844 - sqlite remake issues)
        """
        operation1 = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
        )
        operation2 = migrations.CreateModel(
            "Rider",
            [
                ("id", models.AutoField(primary_key=True)),
                ("number", models.IntegerField(default=1)),
                ("pony", models.ForeignKey("test_crmoua.Pony", models.CASCADE)),
            ],
        )
        operation3 = migrations.AlterUniqueTogether(
            "Rider",
            [
                ("number", "pony"),
            ],
        )
        # Test the database alteration
        project_state = ProjectState()
        self.assertTableNotExists("test_crmoua_pony")
        self.assertTableNotExists("test_crmoua_rider")
        with connection.schema_editor() as editor:
            new_state = project_state.clone()
            operation1.state_forwards("test_crmoua", new_state)
            operation1.database_forwards(
                "test_crmoua", editor, project_state, new_state
            )
            project_state, new_state = new_state, new_state.clone()
            operation2.state_forwards("test_crmoua", new_state)
            operation2.database_forwards(
                "test_crmoua", editor, project_state, new_state
            )
            project_state, new_state = new_state, new_state.clone()
            operation3.state_forwards("test_crmoua", new_state)
            operation3.database_forwards(
                "test_crmoua", editor, project_state, new_state
            )
        self.assertTableExists("test_crmoua_pony")
        self.assertTableExists("test_crmoua_rider")

    def test_create_model_m2m(self):
        """
        Test the creation of a model with a ManyToMany field and the
        auto-created "through" model.
        """
        project_state = self.set_up_test_model("test_crmomm")
        operation = migrations.CreateModel(
            "Stable",
            [
                ("id", models.AutoField(primary_key=True)),
                ("ponies", models.ManyToManyField("Pony", related_name="stables")),
            ],
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_crmomm", new_state)
        # Test the database alteration
        self.assertTableNotExists("test_crmomm_stable_ponies")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmomm", editor, project_state, new_state)
        self.assertTableExists("test_crmomm_stable")
        self.assertTableExists("test_crmomm_stable_ponies")
        self.assertColumnNotExists("test_crmomm_stable", "ponies")
        # Make sure the M2M field actually works
        with atomic():
            Pony = new_state.apps.get_model("test_crmomm", "Pony")
            Stable = new_state.apps.get_model("test_crmomm", "Stable")
            stable = Stable.objects.create()
            p1 = Pony.objects.create(pink=False, weight=4.55)
            p2 = Pony.objects.create(pink=True, weight=5.43)
            stable.ponies.add(p1, p2)
            self.assertEqual(stable.ponies.count(), 2)
            stable.ponies.all().delete()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_crmomm", editor, new_state, project_state
            )
        self.assertTableNotExists("test_crmomm_stable")
        self.assertTableNotExists("test_crmomm_stable_ponies")

    @skipUnlessDBFeature("supports_collation_on_charfield", "supports_foreign_keys")
    def test_create_fk_models_to_pk_field_db_collation(self):
        """Creation of models with a FK to a PK with db_collation."""
        collation = connection.features.test_collations.get("non_default")
        if not collation:
            self.skipTest("Language collations are not supported.")

        app_label = "test_cfkmtopkfdbc"
        operations = [
            migrations.CreateModel(
                "Pony",
                [
                    (
                        "id",
                        models.CharField(
                            primary_key=True,
                            max_length=10,
                            db_collation=collation,
                        ),
                    ),
                ],
            )
        ]
        project_state = self.apply_operations(app_label, ProjectState(), operations)
        # ForeignKey.
        new_state = project_state.clone()
        operation = migrations.CreateModel(
            "Rider",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pony", models.ForeignKey("Pony", models.CASCADE)),
            ],
        )
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnCollation(f"{app_label}_rider", "pony_id", collation)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        # OneToOneField.
        new_state = project_state.clone()
        operation = migrations.CreateModel(
            "ShetlandPony",
            [
                (
                    "pony",
                    models.OneToOneField("Pony", models.CASCADE, primary_key=True),
                ),
                ("cuteness", models.IntegerField(default=1)),
            ],
        )
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnCollation(f"{app_label}_shetlandpony", "pony_id", collation)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)

    def test_create_model_inheritance(self):
        """
        Tests the CreateModel operation on a multi-table inheritance setup.
        """
        project_state = self.set_up_test_model("test_crmoih")
        # Test the state alteration
        operation = migrations.CreateModel(
            "ShetlandPony",
            [
                (
                    "pony_ptr",
                    models.OneToOneField(
                        "test_crmoih.Pony",
                        models.CASCADE,
                        auto_created=True,
                        primary_key=True,
                        to_field="id",
                        serialize=False,
                    ),
                ),
                ("cuteness", models.IntegerField(default=1)),
            ],
        )
        new_state = project_state.clone()
        operation.state_forwards("test_crmoih", new_state)
        self.assertIn(("test_crmoih", "shetlandpony"), new_state.models)
        # Test the database alteration
        self.assertTableNotExists("test_crmoih_shetlandpony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmoih", editor, project_state, new_state)
        self.assertTableExists("test_crmoih_shetlandpony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_crmoih", editor, new_state, project_state
            )
        self.assertTableNotExists("test_crmoih_shetlandpony")

    def test_create_proxy_model(self):
        """
        CreateModel ignores proxy models.
        """
        project_state = self.set_up_test_model("test_crprmo")
        # Test the state alteration
        operation = migrations.CreateModel(
            "ProxyPony",
            [],
            options={"proxy": True},
            bases=("test_crprmo.Pony",),
        )
        self.assertEqual(operation.describe(), "Create proxy model ProxyPony")
        new_state = project_state.clone()
        operation.state_forwards("test_crprmo", new_state)
        self.assertIn(("test_crprmo", "proxypony"), new_state.models)
        # Test the database alteration
        self.assertTableNotExists("test_crprmo_proxypony")
        self.assertTableExists("test_crprmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crprmo", editor, project_state, new_state)
        self.assertTableNotExists("test_crprmo_proxypony")
        self.assertTableExists("test_crprmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_crprmo", editor, new_state, project_state
            )
        self.assertTableNotExists("test_crprmo_proxypony")
        self.assertTableExists("test_crprmo_pony")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["bases", "fields", "name", "options"])

    def test_create_unmanaged_model(self):
        """
        CreateModel ignores unmanaged models.
        """
        project_state = self.set_up_test_model("test_crummo")
        # Test the state alteration
        operation = migrations.CreateModel(
            "UnmanagedPony",
            [],
            options={"proxy": True},
            bases=("test_crummo.Pony",),
        )
        self.assertEqual(operation.describe(), "Create proxy model UnmanagedPony")
        new_state = project_state.clone()
        operation.state_forwards("test_crummo", new_state)
        self.assertIn(("test_crummo", "unmanagedpony"), new_state.models)
        # Test the database alteration
        self.assertTableNotExists("test_crummo_unmanagedpony")
        self.assertTableExists("test_crummo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crummo", editor, project_state, new_state)
        self.assertTableNotExists("test_crummo_unmanagedpony")
        self.assertTableExists("test_crummo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_crummo", editor, new_state, project_state
            )
        self.assertTableNotExists("test_crummo_unmanagedpony")
        self.assertTableExists("test_crummo_pony")

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_create_model_with_constraint(self):
        where = models.Q(pink__gt=2)
        check_constraint = models.CheckConstraint(
            check=where, name="test_constraint_pony_pink_gt_2"
        )
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
            ],
            options={"constraints": [check_constraint]},
        )

        # Test the state alteration
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        self.assertEqual(
            len(new_state.models["test_crmo", "pony"].options["constraints"]), 1
        )

        # Test database alteration
        self.assertTableNotExists("test_crmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableExists("test_crmo_pony")
        with connection.cursor() as cursor:
            with self.assertRaises(IntegrityError):
                cursor.execute("INSERT INTO test_crmo_pony (id, pink) VALUES (1, 1)")

        # Test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")

        # Test deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2]["options"]["constraints"], [check_constraint])

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_create_model_with_boolean_expression_in_check_constraint(self):
        app_label = "test_crmobechc"
        rawsql_constraint = models.CheckConstraint(
            check=models.expressions.RawSQL(
                "price < %s", (1000,), output_field=models.BooleanField()
            ),
            name=f"{app_label}_price_lt_1000_raw",
        )
        wrapper_constraint = models.CheckConstraint(
            check=models.expressions.ExpressionWrapper(
                models.Q(price__gt=500) | models.Q(price__lt=500),
                output_field=models.BooleanField(),
            ),
            name=f"{app_label}_price_neq_500_wrap",
        )
        operation = migrations.CreateModel(
            "Product",
            [
                ("id", models.AutoField(primary_key=True)),
                ("price", models.IntegerField(null=True)),
            ],
            options={"constraints": [rawsql_constraint, wrapper_constraint]},
        )

        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        # Add table.
        self.assertTableNotExists(app_label)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertTableExists(f"{app_label}_product")
        insert_sql = f"INSERT INTO {app_label}_product (id, price) VALUES (%d, %d)"
        with connection.cursor() as cursor:
            with self.assertRaises(IntegrityError):
                cursor.execute(insert_sql % (1, 1000))
            cursor.execute(insert_sql % (1, 999))
            with self.assertRaises(IntegrityError):
                cursor.execute(insert_sql % (2, 500))
            cursor.execute(insert_sql % (2, 499))

    def test_create_model_with_partial_unique_constraint(self):
        partial_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            condition=models.Q(weight__gt=5),
            name="test_constraint_pony_pink_for_weight_gt_5_uniq",
        )
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
            options={"constraints": [partial_unique_constraint]},
        )
        # Test the state alteration
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        self.assertEqual(
            len(new_state.models["test_crmo", "pony"].options["constraints"]), 1
        )
        # Test database alteration
        self.assertTableNotExists("test_crmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableExists("test_crmo_pony")
        # Test constraint works
        Pony = new_state.apps.get_model("test_crmo", "Pony")
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=6.0)
        if connection.features.supports_partial_indexes:
            with self.assertRaises(IntegrityError):
                Pony.objects.create(pink=1, weight=7.0)
        else:
            Pony.objects.create(pink=1, weight=7.0)
        # Test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
        # Test deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2]["options"]["constraints"], [partial_unique_constraint]
        )

    def test_create_model_with_deferred_unique_constraint(self):
        deferred_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            name="deferrable_pink_constraint",
            deferrable=models.Deferrable.DEFERRED,
        )
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
            ],
            options={"constraints": [deferred_unique_constraint]},
        )
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        self.assertEqual(
            len(new_state.models["test_crmo", "pony"].options["constraints"]), 1
        )
        self.assertTableNotExists("test_crmo_pony")
        # Create table.
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableExists("test_crmo_pony")
        Pony = new_state.apps.get_model("test_crmo", "Pony")
        Pony.objects.create(pink=1)
        if connection.features.supports_deferrable_unique_constraints:
            # Unique constraint is deferred.
            with transaction.atomic():
                obj = Pony.objects.create(pink=1)
                obj.pink = 2
                obj.save()
            # Constraint behavior can be changed with SET CONSTRAINTS.
            with self.assertRaises(IntegrityError):
                with transaction.atomic(), connection.cursor() as cursor:
                    quoted_name = connection.ops.quote_name(
                        deferred_unique_constraint.name
                    )
                    cursor.execute("SET CONSTRAINTS %s IMMEDIATE" % quoted_name)
                    obj = Pony.objects.create(pink=1)
                    obj.pink = 3
                    obj.save()
        else:
            Pony.objects.create(pink=1)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2]["options"]["constraints"],
            [deferred_unique_constraint],
        )

    @skipUnlessDBFeature("supports_covering_indexes")
    def test_create_model_with_covering_unique_constraint(self):
        covering_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            include=["weight"],
            name="test_constraint_pony_pink_covering_weight",
        )
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
            options={"constraints": [covering_unique_constraint]},
        )
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        self.assertEqual(
            len(new_state.models["test_crmo", "pony"].options["constraints"]), 1
        )
        self.assertTableNotExists("test_crmo_pony")
        # Create table.
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableExists("test_crmo_pony")
        Pony = new_state.apps.get_model("test_crmo", "Pony")
        Pony.objects.create(pink=1, weight=4.0)
        with self.assertRaises(IntegrityError):
            Pony.objects.create(pink=1, weight=7.0)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2]["options"]["constraints"],
            [covering_unique_constraint],
        )

    def test_create_model_managers(self):
        """
        The managers on a model are set.
        """
        project_state = self.set_up_test_model("test_cmoma")
        # Test the state alteration
        operation = migrations.CreateModel(
            "Food",
            fields=[
                ("id", models.AutoField(primary_key=True)),
            ],
            managers=[
                ("food_qs", FoodQuerySet.as_manager()),
                ("food_mgr", FoodManager("a", "b")),
                ("food_mgr_kwargs", FoodManager("x", "y", 3, 4)),
            ],
        )
        self.assertEqual(operation.describe(), "Create model Food")
        new_state = project_state.clone()
        operation.state_forwards("test_cmoma", new_state)
        self.assertIn(("test_cmoma", "food"), new_state.models)
        managers = new_state.models["test_cmoma", "food"].managers
        self.assertEqual(managers[0][0], "food_qs")
        self.assertIsInstance(managers[0][1], models.Manager)
        self.assertEqual(managers[1][0], "food_mgr")
        self.assertIsInstance(managers[1][1], FoodManager)
        self.assertEqual(managers[1][1].args, ("a", "b", 1, 2))
        self.assertEqual(managers[2][0], "food_mgr_kwargs")
        self.assertIsInstance(managers[2][1], FoodManager)
        self.assertEqual(managers[2][1].args, ("x", "y", 3, 4))

    def test_delete_model(self):
        """
        Tests the DeleteModel operation.
        """
        project_state = self.set_up_test_model("test_dlmo")
        # Test the state alteration
        operation = migrations.DeleteModel("Pony")
        self.assertEqual(operation.describe(), "Delete model Pony")
        self.assertEqual(operation.migration_name_fragment, "delete_pony")
        new_state = project_state.clone()
        operation.state_forwards("test_dlmo", new_state)
        self.assertNotIn(("test_dlmo", "pony"), new_state.models)
        # Test the database alteration
        self.assertTableExists("test_dlmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_dlmo", editor, project_state, new_state)
        self.assertTableNotExists("test_dlmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_dlmo", editor, new_state, project_state)
        self.assertTableExists("test_dlmo_pony")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "DeleteModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(list(definition[2]), ["name"])

    def test_delete_proxy_model(self):
        """
        Tests the DeleteModel operation ignores proxy models.
        """
        project_state = self.set_up_test_model("test_dlprmo", proxy_model=True)
        # Test the state alteration
        operation = migrations.DeleteModel("ProxyPony")
        new_state = project_state.clone()
        operation.state_forwards("test_dlprmo", new_state)
        self.assertIn(("test_dlprmo", "proxypony"), project_state.models)
        self.assertNotIn(("test_dlprmo", "proxypony"), new_state.models)
        # Test the database alteration
        self.assertTableExists("test_dlprmo_pony")
        self.assertTableNotExists("test_dlprmo_proxypony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_dlprmo", editor, project_state, new_state)
        self.assertTableExists("test_dlprmo_pony")
        self.assertTableNotExists("test_dlprmo_proxypony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_dlprmo", editor, new_state, project_state
            )
        self.assertTableExists("test_dlprmo_pony")
        self.assertTableNotExists("test_dlprmo_proxypony")

    def test_delete_mti_model(self):
        project_state = self.set_up_test_model("test_dlmtimo", mti_model=True)
        # Test the state alteration
        operation = migrations.DeleteModel("ShetlandPony")
        new_state = project_state.clone()
        operation.state_forwards("test_dlmtimo", new_state)
        self.assertIn(("test_dlmtimo", "shetlandpony"), project_state.models)
        self.assertNotIn(("test_dlmtimo", "shetlandpony"), new_state.models)
        # Test the database alteration
        self.assertTableExists("test_dlmtimo_pony")
        self.assertTableExists("test_dlmtimo_shetlandpony")
        self.assertColumnExists("test_dlmtimo_shetlandpony", "pony_ptr_id")
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_dlmtimo", editor, project_state, new_state
            )
        self.assertTableExists("test_dlmtimo_pony")
        self.assertTableNotExists("test_dlmtimo_shetlandpony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_dlmtimo", editor, new_state, project_state
            )
        self.assertTableExists("test_dlmtimo_pony")
        self.assertTableExists("test_dlmtimo_shetlandpony")
        self.assertColumnExists("test_dlmtimo_shetlandpony", "pony_ptr_id")

    def test_rename_model(self):
        """
        Tests the RenameModel operation.
        """
        project_state = self.set_up_test_model("test_rnmo", related_model=True)
        # Test the state alteration
        operation = migrations.RenameModel("Pony", "Horse")
        self.assertEqual(operation.describe(), "Rename model Pony to Horse")
        self.assertEqual(operation.migration_name_fragment, "rename_pony_horse")
        # Test initial state and database
        self.assertIn(("test_rnmo", "pony"), project_state.models)
        self.assertNotIn(("test_rnmo", "horse"), project_state.models)
        self.assertTableExists("test_rnmo_pony")
        self.assertTableNotExists("test_rnmo_horse")
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                "test_rnmo_rider", ["pony_id"], ("test_rnmo_pony", "id")
            )
            self.assertFKNotExists(
                "test_rnmo_rider", ["pony_id"], ("test_rnmo_horse", "id")
            )
        # Migrate forwards
        new_state = project_state.clone()
        atomic_rename = connection.features.supports_atomic_references_rename
        new_state = self.apply_operations(
            "test_rnmo", new_state, [operation], atomic=atomic_rename
        )
        # Test new state and database
        self.assertNotIn(("test_rnmo", "pony"), new_state.models)
        self.assertIn(("test_rnmo", "horse"), new_state.models)
        # RenameModel also repoints all incoming FKs and M2Ms
        self.assertEqual(
            new_state.models["test_rnmo", "rider"].fields["pony"].remote_field.model,
            "test_rnmo.Horse",
        )
        self.assertTableNotExists("test_rnmo_pony")
        self.assertTableExists("test_rnmo_horse")
        if connection.features.supports_foreign_keys:
            self.assertFKNotExists(
                "test_rnmo_rider", ["pony_id"], ("test_rnmo_pony", "id")
            )
            self.assertFKExists(
                "test_rnmo_rider", ["pony_id"], ("test_rnmo_horse", "id")
            )
        # Migrate backwards
        original_state = self.unapply_operations(
            "test_rnmo", project_state, [operation], atomic=atomic_rename
        )
        # Test original state and database
        self.assertIn(("test_rnmo", "pony"), original_state.models)
        self.assertNotIn(("test_rnmo", "horse"), original_state.models)
        self.assertEqual(
            original_state.models["test_rnmo", "rider"]
            .fields["pony"]
            .remote_field.model,
            "Pony",
        )
        self.assertTableExists("test_rnmo_pony")
        self.assertTableNotExists("test_rnmo_horse")
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                "test_rnmo_rider", ["pony_id"], ("test_rnmo_pony", "id")
            )
            self.assertFKNotExists(
                "test_rnmo_rider", ["pony_id"], ("test_rnmo_horse", "id")
            )
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RenameModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"old_name": "Pony", "new_name": "Horse"})

    def test_rename_model_state_forwards(self):
        """
        RenameModel operations shouldn't trigger the caching of rendered apps
        on state without prior apps.
        """
        state = ProjectState()
        state.add_model(ModelState("migrations", "Foo", []))
        operation = migrations.RenameModel("Foo", "Bar")
        operation.state_forwards("migrations", state)
        self.assertNotIn("apps", state.__dict__)
        self.assertNotIn(("migrations", "foo"), state.models)
        self.assertIn(("migrations", "bar"), state.models)
        # Now with apps cached.
        apps = state.apps
        operation = migrations.RenameModel("Bar", "Foo")
        operation.state_forwards("migrations", state)
        self.assertIs(state.apps, apps)
        self.assertNotIn(("migrations", "bar"), state.models)
        self.assertIn(("migrations", "foo"), state.models)

    def test_rename_model_with_self_referential_fk(self):
        """
        Tests the RenameModel operation on model with self referential FK.
        """
        project_state = self.set_up_test_model("test_rmwsrf", related_model=True)
        # Test the state alteration
        operation = migrations.RenameModel("Rider", "HorseRider")
        self.assertEqual(operation.describe(), "Rename model Rider to HorseRider")
        new_state = project_state.clone()
        operation.state_forwards("test_rmwsrf", new_state)
        self.assertNotIn(("test_rmwsrf", "rider"), new_state.models)
        self.assertIn(("test_rmwsrf", "horserider"), new_state.models)
        # Remember, RenameModel also repoints all incoming FKs and M2Ms
        self.assertEqual(
            "self",
            new_state.models["test_rmwsrf", "horserider"]
            .fields["friend"]
            .remote_field.model,
        )
        HorseRider = new_state.apps.get_model("test_rmwsrf", "horserider")
        self.assertIs(
            HorseRider._meta.get_field("horserider").remote_field.model, HorseRider
        )
        # Test the database alteration
        self.assertTableExists("test_rmwsrf_rider")
        self.assertTableNotExists("test_rmwsrf_horserider")
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                "test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_rider", "id")
            )
            self.assertFKNotExists(
                "test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_horserider", "id")
            )
        atomic_rename = connection.features.supports_atomic_references_rename
        with connection.schema_editor(atomic=atomic_rename) as editor:
            operation.database_forwards("test_rmwsrf", editor, project_state, new_state)
        self.assertTableNotExists("test_rmwsrf_rider")
        self.assertTableExists("test_rmwsrf_horserider")
        if connection.features.supports_foreign_keys:
            self.assertFKNotExists(
                "test_rmwsrf_horserider", ["friend_id"], ("test_rmwsrf_rider", "id")
            )
            self.assertFKExists(
                "test_rmwsrf_horserider",
                ["friend_id"],
                ("test_rmwsrf_horserider", "id"),
            )
        # And test reversal
        with connection.schema_editor(atomic=atomic_rename) as editor:
            operation.database_backwards(
                "test_rmwsrf", editor, new_state, project_state
            )
        self.assertTableExists("test_rmwsrf_rider")
        self.assertTableNotExists("test_rmwsrf_horserider")
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                "test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_rider", "id")
            )
            self.assertFKNotExists(
                "test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_horserider", "id")
            )

    def test_rename_model_with_superclass_fk(self):
        """
        Tests the RenameModel operation on a model which has a superclass that
        has a foreign key.
        """
        project_state = self.set_up_test_model(
            "test_rmwsc", related_model=True, mti_model=True
        )
        # Test the state alteration
        operation = migrations.RenameModel("ShetlandPony", "LittleHorse")
        self.assertEqual(
            operation.describe(), "Rename model ShetlandPony to LittleHorse"
        )
        new_state = project_state.clone()
        operation.state_forwards("test_rmwsc", new_state)
        self.assertNotIn(("test_rmwsc", "shetlandpony"), new_state.models)
        self.assertIn(("test_rmwsc", "littlehorse"), new_state.models)
        # RenameModel shouldn't repoint the superclass's relations, only local ones
        self.assertEqual(
            project_state.models["test_rmwsc", "rider"]
            .fields["pony"]
            .remote_field.model,
            new_state.models["test_rmwsc", "rider"].fields["pony"].remote_field.model,
        )
        # Before running the migration we have a table for Shetland Pony, not
        # Little Horse.
        self.assertTableExists("test_rmwsc_shetlandpony")
        self.assertTableNotExists("test_rmwsc_littlehorse")
        if connection.features.supports_foreign_keys:
            # and the foreign key on rider points to pony, not shetland pony
            self.assertFKExists(
                "test_rmwsc_rider", ["pony_id"], ("test_rmwsc_pony", "id")
            )
            self.assertFKNotExists(
                "test_rmwsc_rider", ["pony_id"], ("test_rmwsc_shetlandpony", "id")
            )
        with connection.schema_editor(
            atomic=connection.features.supports_atomic_references_rename
        ) as editor:
            operation.database_forwards("test_rmwsc", editor, project_state, new_state)
        # Now we have a little horse table, not shetland pony
        self.assertTableNotExists("test_rmwsc_shetlandpony")
        self.assertTableExists("test_rmwsc_littlehorse")
        if connection.features.supports_foreign_keys:
            # but the Foreign keys still point at pony, not little horse
            self.assertFKExists(
                "test_rmwsc_rider", ["pony_id"], ("test_rmwsc_pony", "id")
            )
            self.assertFKNotExists(
                "test_rmwsc_rider", ["pony_id"], ("test_rmwsc_littlehorse", "id")
            )

    def test_rename_model_no_relations_with_db_table_noop(self):
        app_label = "test_rmwdbtnoop"
        project_state = self.set_up_test_model(app_label, db_table="my_pony")
        operation = migrations.RenameModel("Pony", "LittleHorse")
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            operation.database_forwards(app_label, editor, project_state, new_state)

    @skipUnlessDBFeature("supports_foreign_keys")
    def test_rename_model_with_db_table_and_fk_noop(self):
        app_label = "test_rmwdbtfk"
        project_state = self.set_up_test_model(
            app_label, db_table="my_pony", related_model=True
        )
        new_state = project_state.clone()
        operation = migrations.RenameModel("Pony", "LittleHorse")
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            operation.database_forwards(app_label, editor, project_state, new_state)

    def test_rename_model_with_self_referential_m2m(self):
        app_label = "test_rename_model_with_self_referential_m2m"

        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "ReflexivePony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("ponies", models.ManyToManyField("self")),
                    ],
                ),
            ],
        )
        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.RenameModel("ReflexivePony", "ReflexivePony2"),
            ],
            atomic=connection.features.supports_atomic_references_rename,
        )
        Pony = project_state.apps.get_model(app_label, "ReflexivePony2")
        pony = Pony.objects.create()
        pony.ponies.add(pony)

    def test_rename_model_with_m2m(self):
        app_label = "test_rename_model_with_m2m"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("riders", models.ManyToManyField("Rider")),
                    ],
                ),
            ],
        )
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)

        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.RenameModel("Pony", "Pony2"),
            ],
            atomic=connection.features.supports_atomic_references_rename,
        )
        Pony = project_state.apps.get_model(app_label, "Pony2")
        Rider = project_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)
        self.assertEqual(Pony.objects.count(), 2)
        self.assertEqual(Rider.objects.count(), 2)
        self.assertEqual(
            Pony._meta.get_field("riders").remote_field.through.objects.count(), 2
        )

    def test_rename_model_with_m2m_models_in_different_apps_with_same_name(self):
        app_label_1 = "test_rmw_m2m_1"
        app_label_2 = "test_rmw_m2m_2"
        project_state = self.apply_operations(
            app_label_1,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
            ],
        )
        project_state = self.apply_operations(
            app_label_2,
            project_state,
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("riders", models.ManyToManyField(f"{app_label_1}.Rider")),
                    ],
                ),
            ],
        )
        m2m_table = f"{app_label_2}_rider_riders"
        self.assertColumnExists(m2m_table, "from_rider_id")
        self.assertColumnExists(m2m_table, "to_rider_id")

        Rider_1 = project_state.apps.get_model(app_label_1, "Rider")
        Rider_2 = project_state.apps.get_model(app_label_2, "Rider")
        rider_2 = Rider_2.objects.create()
        rider_2.riders.add(Rider_1.objects.create())
        # Rename model.
        project_state_2 = project_state.clone()
        project_state = self.apply_operations(
            app_label_2,
            project_state,
            operations=[migrations.RenameModel("Rider", "Pony")],
            atomic=connection.features.supports_atomic_references_rename,
        )

        m2m_table = f"{app_label_2}_pony_riders"
        self.assertColumnExists(m2m_table, "pony_id")
        self.assertColumnExists(m2m_table, "rider_id")

        Rider_1 = project_state.apps.get_model(app_label_1, "Rider")
        Rider_2 = project_state.apps.get_model(app_label_2, "Pony")
        rider_2 = Rider_2.objects.create()
        rider_2.riders.add(Rider_1.objects.create())
        self.assertEqual(Rider_1.objects.count(), 2)
        self.assertEqual(Rider_2.objects.count(), 2)
        self.assertEqual(
            Rider_2._meta.get_field("riders").remote_field.through.objects.count(), 2
        )
        # Reversal.
        self.unapply_operations(
            app_label_2,
            project_state_2,
            operations=[migrations.RenameModel("Rider", "Pony")],
            atomic=connection.features.supports_atomic_references_rename,
        )
        m2m_table = f"{app_label_2}_rider_riders"
        self.assertColumnExists(m2m_table, "to_rider_id")
        self.assertColumnExists(m2m_table, "from_rider_id")

    def test_rename_model_with_db_table_rename_m2m(self):
        app_label = "test_rmwdbrm2m"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("riders", models.ManyToManyField("Rider")),
                    ],
                    options={"db_table": "pony"},
                ),
            ],
        )
        new_state = self.apply_operations(
            app_label,
            project_state,
            operations=[migrations.RenameModel("Pony", "PinkPony")],
            atomic=connection.features.supports_atomic_references_rename,
        )
        Pony = new_state.apps.get_model(app_label, "PinkPony")
        Rider = new_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)

    def test_rename_m2m_target_model(self):
        app_label = "test_rename_m2m_target_model"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("riders", models.ManyToManyField("Rider")),
                    ],
                ),
            ],
        )
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)

        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.RenameModel("Rider", "Rider2"),
            ],
            atomic=connection.features.supports_atomic_references_rename,
        )
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider2")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)
        self.assertEqual(Pony.objects.count(), 2)
        self.assertEqual(Rider.objects.count(), 2)
        self.assertEqual(
            Pony._meta.get_field("riders").remote_field.through.objects.count(), 2
        )

    def test_rename_m2m_through_model(self):
        app_label = "test_rename_through"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    "PonyRider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "rider",
                            models.ForeignKey(
                                "test_rename_through.Rider", models.CASCADE
                            ),
                        ),
                        (
                            "pony",
                            models.ForeignKey(
                                "test_rename_through.Pony", models.CASCADE
                            ),
                        ),
                    ],
                ),
                migrations.AddField(
                    "Pony",
                    "riders",
                    models.ManyToManyField(
                        "test_rename_through.Rider",
                        through="test_rename_through.PonyRider",
                    ),
                ),
            ],
        )
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        PonyRider = project_state.apps.get_model(app_label, "PonyRider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        PonyRider.objects.create(pony=pony, rider=rider)

        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.RenameModel("PonyRider", "PonyRider2"),
            ],
        )
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        PonyRider = project_state.apps.get_model(app_label, "PonyRider2")
        pony = Pony.objects.first()
        rider = Rider.objects.create()
        PonyRider.objects.create(pony=pony, rider=rider)
        self.assertEqual(Pony.objects.count(), 1)
        self.assertEqual(Rider.objects.count(), 2)
        self.assertEqual(PonyRider.objects.count(), 2)
        self.assertEqual(pony.riders.count(), 2)

    def test_rename_m2m_model_after_rename_field(self):
        """RenameModel renames a many-to-many column after a RenameField."""
        app_label = "test_rename_multiple"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=20)),
                    ],
                ),
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "pony",
                            models.ForeignKey(
                                "test_rename_multiple.Pony", models.CASCADE
                            ),
                        ),
                    ],
                ),
                migrations.CreateModel(
                    "PonyRider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("riders", models.ManyToManyField("Rider")),
                    ],
                ),
                migrations.RenameField(
                    model_name="pony", old_name="name", new_name="fancy_name"
                ),
                migrations.RenameModel(old_name="Rider", new_name="Jockey"),
            ],
            atomic=connection.features.supports_atomic_references_rename,
        )
        Pony = project_state.apps.get_model(app_label, "Pony")
        Jockey = project_state.apps.get_model(app_label, "Jockey")
        PonyRider = project_state.apps.get_model(app_label, "PonyRider")
        # No "no such column" error means the column was renamed correctly.
        pony = Pony.objects.create(fancy_name="a good name")
        jockey = Jockey.objects.create(pony=pony)
        ponyrider = PonyRider.objects.create()
        ponyrider.riders.add(jockey)

    def test_add_field(self):
        """
        Tests the AddField operation.
        """
        # Test the state alteration
        operation = migrations.AddField(
            "Pony",
            "height",
            models.FloatField(null=True, default=5),
        )
        self.assertEqual(operation.describe(), "Add field height to Pony")
        self.assertEqual(operation.migration_name_fragment, "pony_height")
        project_state, new_state = self.make_test_state("test_adfl", operation)
        self.assertEqual(len(new_state.models["test_adfl", "pony"].fields), 6)
        field = new_state.models["test_adfl", "pony"].fields["height"]
        self.assertEqual(field.default, 5)
        # Test the database alteration
        self.assertColumnNotExists("test_adfl_pony", "height")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adfl", editor, project_state, new_state)
        self.assertColumnExists("test_adfl_pony", "height")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adfl", editor, new_state, project_state)
        self.assertColumnNotExists("test_adfl_pony", "height")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddField")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["field", "model_name", "name"])

    def test_add_charfield(self):
        """
        Tests the AddField operation on TextField.
        """
        project_state = self.set_up_test_model("test_adchfl")

        Pony = project_state.apps.get_model("test_adchfl", "Pony")
        pony = Pony.objects.create(weight=42)

        new_state = self.apply_operations(
            "test_adchfl",
            project_state,
            [
                migrations.AddField(
                    "Pony",
                    "text",
                    models.CharField(max_length=10, default="some text"),
                ),
                migrations.AddField(
                    "Pony",
                    "empty",
                    models.CharField(max_length=10, default=""),
                ),
                # If not properly quoted digits would be interpreted as an int.
                migrations.AddField(
                    "Pony",
                    "digits",
                    models.CharField(max_length=10, default="42"),
                ),
                # Manual quoting is fragile and could trip on quotes. Refs #xyz.
                migrations.AddField(
                    "Pony",
                    "quotes",
                    models.CharField(max_length=10, default='"\'"'),
                ),
            ],
        )

        Pony = new_state.apps.get_model("test_adchfl", "Pony")
        pony = Pony.objects.get(pk=pony.pk)
        self.assertEqual(pony.text, "some text")
        self.assertEqual(pony.empty, "")
        self.assertEqual(pony.digits, "42")
        self.assertEqual(pony.quotes, '"\'"')

    def test_add_textfield(self):
        """
        Tests the AddField operation on TextField.
        """
        project_state = self.set_up_test_model("test_adtxtfl")

        Pony = project_state.apps.get_model("test_adtxtfl", "Pony")
        pony = Pony.objects.create(weight=42)

        new_state = self.apply_operations(
            "test_adtxtfl",
            project_state,
            [
                migrations.AddField(
                    "Pony",
                    "text",
                    models.TextField(default="some text"),
                ),
                migrations.AddField(
                    "Pony",
                    "empty",
                    models.TextField(default=""),
                ),
                # If not properly quoted digits would be interpreted as an int.
                migrations.AddField(
                    "Pony",
                    "digits",
                    models.TextField(default="42"),
                ),
                # Manual quoting is fragile and could trip on quotes. Refs #xyz.
                migrations.AddField(
                    "Pony",
                    "quotes",
                    models.TextField(default='"\'"'),
                ),
            ],
        )

        Pony = new_state.apps.get_model("test_adtxtfl", "Pony")
        pony = Pony.objects.get(pk=pony.pk)
        self.assertEqual(pony.text, "some text")
        self.assertEqual(pony.empty, "")
        self.assertEqual(pony.digits, "42")
        self.assertEqual(pony.quotes, '"\'"')

    def test_add_binaryfield(self):
        """
        Tests the AddField operation on TextField/BinaryField.
        """
        project_state = self.set_up_test_model("test_adbinfl")

        Pony = project_state.apps.get_model("test_adbinfl", "Pony")
        pony = Pony.objects.create(weight=42)

        new_state = self.apply_operations(
            "test_adbinfl",
            project_state,
            [
                migrations.AddField(
                    "Pony",
                    "blob",
                    models.BinaryField(default=b"some text"),
                ),
                migrations.AddField(
                    "Pony",
                    "empty",
                    models.BinaryField(default=b""),
                ),
                # If not properly quoted digits would be interpreted as an int.
                migrations.AddField(
                    "Pony",
                    "digits",
                    models.BinaryField(default=b"42"),
                ),
                # Manual quoting is fragile and could trip on quotes. Refs #xyz.
                migrations.AddField(
                    "Pony",
                    "quotes",
                    models.BinaryField(default=b'"\'"'),
                ),
            ],
        )

        Pony = new_state.apps.get_model("test_adbinfl", "Pony")
        pony = Pony.objects.get(pk=pony.pk)
        # SQLite returns buffer/memoryview, cast to bytes for checking.
        self.assertEqual(bytes(pony.blob), b"some text")
        self.assertEqual(bytes(pony.empty), b"")
        self.assertEqual(bytes(pony.digits), b"42")
        self.assertEqual(bytes(pony.quotes), b'"\'"')

    def test_column_name_quoting(self):
        """
        Column names that are SQL keywords shouldn't cause problems when used
        in migrations (#22168).
        """
        project_state = self.set_up_test_model("test_regr22168")
        operation = migrations.AddField(
            "Pony",
            "order",
            models.IntegerField(default=0),
        )
        new_state = project_state.clone()
        operation.state_forwards("test_regr22168", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_regr22168", editor, project_state, new_state
            )
        self.assertColumnExists("test_regr22168_pony", "order")

    def test_add_field_preserve_default(self):
        """
        Tests the AddField operation's state alteration
        when preserve_default = False.
        """
        project_state = self.set_up_test_model("test_adflpd")
        # Test the state alteration
        operation = migrations.AddField(
            "Pony",
            "height",
            models.FloatField(null=True, default=4),
            preserve_default=False,
        )
        new_state = project_state.clone()
        operation.state_forwards("test_adflpd", new_state)
        self.assertEqual(len(new_state.models["test_adflpd", "pony"].fields), 6)
        field = new_state.models["test_adflpd", "pony"].fields["height"]
        self.assertEqual(field.default, models.NOT_PROVIDED)
        # Test the database alteration
        project_state.apps.get_model("test_adflpd", "pony").objects.create(
            weight=4,
        )
        self.assertColumnNotExists("test_adflpd_pony", "height")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adflpd", editor, project_state, new_state)
        self.assertColumnExists("test_adflpd_pony", "height")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddField")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            sorted(definition[2]), ["field", "model_name", "name", "preserve_default"]
        )

    def test_add_field_database_default(self):
        """The AddField operation can set and unset a database default."""
        app_label = "test_adfldd"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.AddField(
            "Pony", "height", models.FloatField(null=True, db_default=4)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, "pony"].fields), 6)
        field = new_state.models[app_label, "pony"].fields["height"]
        self.assertEqual(field.default, models.NOT_PROVIDED)
        self.assertEqual(field.db_default, Value(4))
        project_state.apps.get_model(app_label, "pony").objects.create(weight=4)
        self.assertColumnNotExists(table_name, "height")
        # Add field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnExists(table_name, "height")
        new_model = new_state.apps.get_model(app_label, "pony")
        old_pony = new_model.objects.get()
        self.assertEqual(old_pony.height, 4)
        new_pony = new_model.objects.create(weight=5)
        if not connection.features.can_return_columns_from_insert:
            new_pony.refresh_from_db()
        self.assertEqual(new_pony.height, 4)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertColumnNotExists(table_name, "height")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddField")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "field": field,
                "model_name": "Pony",
                "name": "height",
            },
        )

    def test_add_field_database_default_special_char_escaping(self):
        app_label = "test_adflddsce"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        old_pony_pk = (
            project_state.apps.get_model(app_label, "pony").objects.create(weight=4).pk
        )
        tests = ["%", "'", '"']
        for db_default in tests:
            with self.subTest(db_default=db_default):
                operation = migrations.AddField(
                    "Pony",
                    "special_char",
                    models.CharField(max_length=1, db_default=db_default),
                )
                new_state = project_state.clone()
                operation.state_forwards(app_label, new_state)
                self.assertEqual(len(new_state.models[app_label, "pony"].fields), 6)
                field = new_state.models[app_label, "pony"].fields["special_char"]
                self.assertEqual(field.default, models.NOT_PROVIDED)
                self.assertEqual(field.db_default, Value(db_default))
                self.assertColumnNotExists(table_name, "special_char")
                with connection.schema_editor() as editor:
                    operation.database_forwards(
                        app_label, editor, project_state, new_state
                    )
                self.assertColumnExists(table_name, "special_char")
                new_model = new_state.apps.get_model(app_label, "pony")
                try:
                    new_pony = new_model.objects.create(weight=5)
                    if not connection.features.can_return_columns_from_insert:
                        new_pony.refresh_from_db()
                    self.assertEqual(new_pony.special_char, db_default)

                    old_pony = new_model.objects.get(pk=old_pony_pk)
                    if connection.vendor != "oracle" or db_default != "'":
                        # The single quotation mark ' is properly quoted and is
                        # set for new rows on Oracle, however it is not set on
                        # existing rows. Skip the assertion as it's probably a
                        # bug in Oracle.
                        self.assertEqual(old_pony.special_char, db_default)
                finally:
                    with connection.schema_editor() as editor:
                        operation.database_backwards(
                            app_label, editor, new_state, project_state
                        )

    @skipUnlessDBFeature("supports_expression_defaults")
    def test_add_field_database_default_function(self):
        app_label = "test_adflddf"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.AddField(
            "Pony", "height", models.FloatField(db_default=Pi())
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, "pony"].fields), 6)
        field = new_state.models[app_label, "pony"].fields["height"]
        self.assertEqual(field.default, models.NOT_PROVIDED)
        self.assertEqual(field.db_default, Pi())
        project_state.apps.get_model(app_label, "pony").objects.create(weight=4)
        self.assertColumnNotExists(table_name, "height")
        # Add field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnExists(table_name, "height")
        new_model = new_state.apps.get_model(app_label, "pony")
        old_pony = new_model.objects.get()
        self.assertAlmostEqual(old_pony.height, math.pi)
        new_pony = new_model.objects.create(weight=5)
        if not connection.features.can_return_columns_from_insert:
            new_pony.refresh_from_db()
        self.assertAlmostEqual(old_pony.height, math.pi)

    def test_add_field_both_defaults(self):
        """The AddField operation with both default and db_default."""
        app_label = "test_adflbddd"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.AddField(
            "Pony", "height", models.FloatField(default=3, db_default=4)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, "pony"].fields), 6)
        field = new_state.models[app_label, "pony"].fields["height"]
        self.assertEqual(field.default, 3)
        self.assertEqual(field.db_default, Value(4))
        project_state.apps.get_model(app_label, "pony").objects.create(weight=4)
        self.assertColumnNotExists(table_name, "height")
        # Add field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnExists(table_name, "height")
        new_model = new_state.apps.get_model(app_label, "pony")
        old_pony = new_model.objects.get()
        self.assertEqual(old_pony.height, 4)
        new_pony = new_model.objects.create(weight=5)
        if not connection.features.can_return_columns_from_insert:
            new_pony.refresh_from_db()
        self.assertEqual(new_pony.height, 3)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertColumnNotExists(table_name, "height")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddField")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "field": field,
                "model_name": "Pony",
                "name": "height",
            },
        )

    def test_add_field_m2m(self):
        """
        Tests the AddField operation with a ManyToManyField.
        """
        project_state = self.set_up_test_model("test_adflmm", second_model=True)
        # Test the state alteration
        operation = migrations.AddField(
            "Pony", "stables", models.ManyToManyField("Stable", related_name="ponies")
        )
        new_state = project_state.clone()
        operation.state_forwards("test_adflmm", new_state)
        self.assertEqual(len(new_state.models["test_adflmm", "pony"].fields), 6)
        # Test the database alteration
        self.assertTableNotExists("test_adflmm_pony_stables")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adflmm", editor, project_state, new_state)
        self.assertTableExists("test_adflmm_pony_stables")
        self.assertColumnNotExists("test_adflmm_pony", "stables")
        # Make sure the M2M field actually works
        with atomic():
            Pony = new_state.apps.get_model("test_adflmm", "Pony")
            p = Pony.objects.create(pink=False, weight=4.55)
            p.stables.create()
            self.assertEqual(p.stables.count(), 1)
            p.stables.all().delete()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_adflmm", editor, new_state, project_state
            )
        self.assertTableNotExists("test_adflmm_pony_stables")

    def test_alter_field_m2m(self):
        project_state = self.set_up_test_model("test_alflmm", second_model=True)

        project_state = self.apply_operations(
            "test_alflmm",
            project_state,
            operations=[
                migrations.AddField(
                    "Pony",
                    "stables",
                    models.ManyToManyField("Stable", related_name="ponies"),
                )
            ],
        )
        Pony = project_state.apps.get_model("test_alflmm", "Pony")
        self.assertFalse(Pony._meta.get_field("stables").blank)

        project_state = self.apply_operations(
            "test_alflmm",
            project_state,
            operations=[
                migrations.AlterField(
                    "Pony",
                    "stables",
                    models.ManyToManyField(
                        to="Stable", related_name="ponies", blank=True
                    ),
                )
            ],
        )
        Pony = project_state.apps.get_model("test_alflmm", "Pony")
        self.assertTrue(Pony._meta.get_field("stables").blank)

    def test_repoint_field_m2m(self):
        project_state = self.set_up_test_model(
            "test_alflmm", second_model=True, third_model=True
        )

        project_state = self.apply_operations(
            "test_alflmm",
            project_state,
            operations=[
                migrations.AddField(
                    "Pony",
                    "places",
                    models.ManyToManyField("Stable", related_name="ponies"),
                )
            ],
        )
        Pony = project_state.apps.get_model("test_alflmm", "Pony")

        project_state = self.apply_operations(
            "test_alflmm",
            project_state,
            operations=[
                migrations.AlterField(
                    "Pony",
                    "places",
                    models.ManyToManyField(to="Van", related_name="ponies"),
                )
            ],
        )

        # Ensure the new field actually works
        Pony = project_state.apps.get_model("test_alflmm", "Pony")
        p = Pony.objects.create(pink=False, weight=4.55)
        p.places.create()
        self.assertEqual(p.places.count(), 1)
        p.places.all().delete()

    def test_remove_field_m2m(self):
        project_state = self.set_up_test_model("test_rmflmm", second_model=True)

        project_state = self.apply_operations(
            "test_rmflmm",
            project_state,
            operations=[
                migrations.AddField(
                    "Pony",
                    "stables",
                    models.ManyToManyField("Stable", related_name="ponies"),
                )
            ],
        )
        self.assertTableExists("test_rmflmm_pony_stables")

        with_field_state = project_state.clone()
        operations = [migrations.RemoveField("Pony", "stables")]
        project_state = self.apply_operations(
            "test_rmflmm", project_state, operations=operations
        )
        self.assertTableNotExists("test_rmflmm_pony_stables")

        # And test reversal
        self.unapply_operations("test_rmflmm", with_field_state, operations=operations)
        self.assertTableExists("test_rmflmm_pony_stables")

    def test_remove_field_m2m_with_through(self):
        project_state = self.set_up_test_model("test_rmflmmwt", second_model=True)

        self.assertTableNotExists("test_rmflmmwt_ponystables")
        project_state = self.apply_operations(
            "test_rmflmmwt",
            project_state,
            operations=[
                migrations.CreateModel(
                    "PonyStables",
                    fields=[
                        (
                            "pony",
                            models.ForeignKey("test_rmflmmwt.Pony", models.CASCADE),
                        ),
                        (
                            "stable",
                            models.ForeignKey("test_rmflmmwt.Stable", models.CASCADE),
                        ),
                    ],
                ),
                migrations.AddField(
                    "Pony",
                    "stables",
                    models.ManyToManyField(
                        "Stable",
                        related_name="ponies",
                        through="test_rmflmmwt.PonyStables",
                    ),
                ),
            ],
        )
        self.assertTableExists("test_rmflmmwt_ponystables")

        operations = [
            migrations.RemoveField("Pony", "stables"),
            migrations.DeleteModel("PonyStables"),
        ]
        self.apply_operations("test_rmflmmwt", project_state, operations=operations)

    def test_remove_field(self):
        """
        Tests the RemoveField operation.
        """
        project_state = self.set_up_test_model("test_rmfl")
        # Test the state alteration
        operation = migrations.RemoveField("Pony", "pink")
        self.assertEqual(operation.describe(), "Remove field pink from Pony")
        self.assertEqual(operation.migration_name_fragment, "remove_pony_pink")
        new_state = project_state.clone()
        operation.state_forwards("test_rmfl", new_state)
        self.assertEqual(len(new_state.models["test_rmfl", "pony"].fields), 4)
        # Test the database alteration
        self.assertColumnExists("test_rmfl_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rmfl", editor, project_state, new_state)
        self.assertColumnNotExists("test_rmfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rmfl", editor, new_state, project_state)
        self.assertColumnExists("test_rmfl_pony", "pink")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveField")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Pony", "name": "pink"})

    def test_remove_fk(self):
        """
        Tests the RemoveField operation on a foreign key.
        """
        project_state = self.set_up_test_model("test_rfk", related_model=True)
        self.assertColumnExists("test_rfk_rider", "pony_id")
        operation = migrations.RemoveField("Rider", "pony")

        new_state = project_state.clone()
        operation.state_forwards("test_rfk", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rfk", editor, project_state, new_state)
        self.assertColumnNotExists("test_rfk_rider", "pony_id")
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rfk", editor, new_state, project_state)
        self.assertColumnExists("test_rfk_rider", "pony_id")

    def test_alter_model_table(self):
        """
        Tests the AlterModelTable operation.
        """
        project_state = self.set_up_test_model("test_almota")
        # Test the state alteration
        operation = migrations.AlterModelTable("Pony", "test_almota_pony_2")
        self.assertEqual(
            operation.describe(), "Rename table for Pony to test_almota_pony_2"
        )
        self.assertEqual(operation.migration_name_fragment, "alter_pony_table")
        new_state = project_state.clone()
        operation.state_forwards("test_almota", new_state)
        self.assertEqual(
            new_state.models["test_almota", "pony"].options["db_table"],
            "test_almota_pony_2",
        )
        # Test the database alteration
        self.assertTableExists("test_almota_pony")
        self.assertTableNotExists("test_almota_pony_2")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_almota", editor, project_state, new_state)
        self.assertTableNotExists("test_almota_pony")
        self.assertTableExists("test_almota_pony_2")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_almota", editor, new_state, project_state
            )
        self.assertTableExists("test_almota_pony")
        self.assertTableNotExists("test_almota_pony_2")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelTable")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"name": "Pony", "table": "test_almota_pony_2"})

    def test_alter_model_table_none(self):
        """
        Tests the AlterModelTable operation if the table name is set to None.
        """
        operation = migrations.AlterModelTable("Pony", None)
        self.assertEqual(operation.describe(), "Rename table for Pony to (default)")

    def test_alter_model_table_noop(self):
        """
        Tests the AlterModelTable operation if the table name is not changed.
        """
        project_state = self.set_up_test_model("test_almota")
        # Test the state alteration
        operation = migrations.AlterModelTable("Pony", "test_almota_pony")
        new_state = project_state.clone()
        operation.state_forwards("test_almota", new_state)
        self.assertEqual(
            new_state.models["test_almota", "pony"].options["db_table"],
            "test_almota_pony",
        )
        # Test the database alteration
        self.assertTableExists("test_almota_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_almota", editor, project_state, new_state)
        self.assertTableExists("test_almota_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_almota", editor, new_state, project_state
            )
        self.assertTableExists("test_almota_pony")

    def test_alter_model_table_m2m(self):
        """
        AlterModelTable should rename auto-generated M2M tables.
        """
        app_label = "test_talflmltlm2m"
        pony_db_table = "pony_foo"
        project_state = self.set_up_test_model(
            app_label, second_model=True, db_table=pony_db_table
        )
        # Add the M2M field
        first_state = project_state.clone()
        operation = migrations.AddField(
            "Pony", "stables", models.ManyToManyField("Stable")
        )
        operation.state_forwards(app_label, first_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, first_state)
        original_m2m_table = "%s_%s" % (pony_db_table, "stables")
        new_m2m_table = "%s_%s" % (app_label, "pony_stables")
        self.assertTableExists(original_m2m_table)
        self.assertTableNotExists(new_m2m_table)
        # Rename the Pony db_table which should also rename the m2m table.
        second_state = first_state.clone()
        operation = migrations.AlterModelTable(name="pony", table=None)
        operation.state_forwards(app_label, second_state)
        atomic_rename = connection.features.supports_atomic_references_rename
        with connection.schema_editor(atomic=atomic_rename) as editor:
            operation.database_forwards(app_label, editor, first_state, second_state)
        self.assertTableExists(new_m2m_table)
        self.assertTableNotExists(original_m2m_table)
        # And test reversal
        with connection.schema_editor(atomic=atomic_rename) as editor:
            operation.database_backwards(app_label, editor, second_state, first_state)
        self.assertTableExists(original_m2m_table)
        self.assertTableNotExists(new_m2m_table)

    def test_alter_model_table_m2m_field(self):
        app_label = "test_talm2mfl"
        project_state = self.set_up_test_model(app_label, second_model=True)
        # Add the M2M field.
        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.AddField(
                    "Pony",
                    "stables",
                    models.ManyToManyField("Stable"),
                )
            ],
        )
        m2m_table = f"{app_label}_pony_stables"
        self.assertColumnExists(m2m_table, "pony_id")
        self.assertColumnExists(m2m_table, "stable_id")
        # Point the M2M field to self.
        with_field_state = project_state.clone()
        operations = [
            migrations.AlterField(
                model_name="Pony",
                name="stables",
                field=models.ManyToManyField("self"),
            )
        ]
        project_state = self.apply_operations(
            app_label, project_state, operations=operations
        )
        self.assertColumnExists(m2m_table, "from_pony_id")
        self.assertColumnExists(m2m_table, "to_pony_id")
        # Reversal.
        self.unapply_operations(app_label, with_field_state, operations=operations)
        self.assertColumnExists(m2m_table, "pony_id")
        self.assertColumnExists(m2m_table, "stable_id")

    def test_alter_field(self):
        """
        Tests the AlterField operation.
        """
        project_state = self.set_up_test_model("test_alfl")
        # Test the state alteration
        operation = migrations.AlterField(
            "Pony", "pink", models.IntegerField(null=True)
        )
        self.assertEqual(operation.describe(), "Alter field pink on Pony")
        self.assertEqual(operation.migration_name_fragment, "alter_pony_pink")
        new_state = project_state.clone()
        operation.state_forwards("test_alfl", new_state)
        self.assertIs(
            project_state.models["test_alfl", "pony"].fields["pink"].null, False
        )
        self.assertIs(new_state.models["test_alfl", "pony"].fields["pink"].null, True)
        # Test the database alteration
        self.assertColumnNotNull("test_alfl_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alfl", editor, project_state, new_state)
        self.assertColumnNull("test_alfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alfl", editor, new_state, project_state)
        self.assertColumnNotNull("test_alfl_pony", "pink")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterField")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["field", "model_name", "name"])

    def test_alter_field_add_database_default(self):
        app_label = "test_alfladd"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.AlterField(
            "Pony", "weight", models.FloatField(db_default=4.5)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        old_weight = project_state.models[app_label, "pony"].fields["weight"]
        self.assertIs(old_weight.db_default, models.NOT_PROVIDED)
        new_weight = new_state.models[app_label, "pony"].fields["weight"]
        self.assertEqual(new_weight.db_default, Value(4.5))
        with self.assertRaises(IntegrityError), transaction.atomic():
            project_state.apps.get_model(app_label, "pony").objects.create()
        # Alter field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        pony = new_state.apps.get_model(app_label, "pony").objects.create()
        if not connection.features.can_return_columns_from_insert:
            pony.refresh_from_db()
        self.assertEqual(pony.weight, 4.5)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        with self.assertRaises(IntegrityError), transaction.atomic():
            project_state.apps.get_model(app_label, "pony").objects.create()
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterField")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "field": new_weight,
                "model_name": "Pony",
                "name": "weight",
            },
        )

    def test_alter_field_change_default_to_database_default(self):
        """The AlterField operation changing default to db_default."""
        app_label = "test_alflcdtdd"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.AlterField(
            "Pony", "pink", models.IntegerField(db_default=4)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        old_pink = project_state.models[app_label, "pony"].fields["pink"]
        self.assertEqual(old_pink.default, 3)
        self.assertIs(old_pink.db_default, models.NOT_PROVIDED)
        new_pink = new_state.models[app_label, "pony"].fields["pink"]
        self.assertIs(new_pink.default, models.NOT_PROVIDED)
        self.assertEqual(new_pink.db_default, Value(4))
        pony = project_state.apps.get_model(app_label, "pony").objects.create(weight=1)
        self.assertEqual(pony.pink, 3)
        # Alter field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        pony = new_state.apps.get_model(app_label, "pony").objects.create(weight=1)
        if not connection.features.can_return_columns_from_insert:
            pony.refresh_from_db()
        self.assertEqual(pony.pink, 4)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        pony = project_state.apps.get_model(app_label, "pony").objects.create(weight=1)
        self.assertEqual(pony.pink, 3)

    def test_alter_field_change_nullable_to_database_default_not_null(self):
        """
        The AlterField operation changing a null field to db_default.
        """
        app_label = "test_alflcntddnn"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.AlterField(
            "Pony", "green", models.IntegerField(db_default=4)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        old_green = project_state.models[app_label, "pony"].fields["green"]
        self.assertIs(old_green.db_default, models.NOT_PROVIDED)
        new_green = new_state.models[app_label, "pony"].fields["green"]
        self.assertEqual(new_green.db_default, Value(4))
        old_pony = project_state.apps.get_model(app_label, "pony").objects.create(
            weight=1
        )
        self.assertIsNone(old_pony.green)
        # Alter field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        old_pony.refresh_from_db()
        self.assertEqual(old_pony.green, 4)
        pony = new_state.apps.get_model(app_label, "pony").objects.create(weight=1)
        if not connection.features.can_return_columns_from_insert:
            pony.refresh_from_db()
        self.assertEqual(pony.green, 4)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        pony = project_state.apps.get_model(app_label, "pony").objects.create(weight=1)
        self.assertIsNone(pony.green)

    @skipIfDBFeature("interprets_empty_strings_as_nulls")
    def test_alter_field_change_blank_nullable_database_default_to_not_null(self):
        app_label = "test_alflcbnddnn"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        default = "Yellow"
        operation = migrations.AlterField(
            "Pony",
            "yellow",
            models.CharField(blank=True, db_default=default, max_length=20),
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertColumnNull(table_name, "yellow")
        pony = project_state.apps.get_model(app_label, "pony").objects.create(
            weight=1, yellow=None
        )
        self.assertIsNone(pony.yellow)
        # Alter field.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnNotNull(table_name, "yellow")
        pony.refresh_from_db()
        self.assertEqual(pony.yellow, default)
        pony = new_state.apps.get_model(app_label, "pony").objects.create(weight=1)
        if not connection.features.can_return_columns_from_insert:
            pony.refresh_from_db()
        self.assertEqual(pony.yellow, default)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertColumnNull(table_name, "yellow")
        pony = project_state.apps.get_model(app_label, "pony").objects.create(
            weight=1, yellow=None
        )
        self.assertIsNone(pony.yellow)

    def test_alter_field_add_db_column_noop(self):
        """
        AlterField operation is a noop when adding only a db_column and the
        column name is not changed.
        """
        app_label = "test_afadbn"
        project_state = self.set_up_test_model(app_label, related_model=True)
        pony_table = "%s_pony" % app_label
        new_state = project_state.clone()
        operation = migrations.AlterField(
            "Pony", "weight", models.FloatField(db_column="weight")
        )
        operation.state_forwards(app_label, new_state)
        self.assertIsNone(
            project_state.models[app_label, "pony"].fields["weight"].db_column,
        )
        self.assertEqual(
            new_state.models[app_label, "pony"].fields["weight"].db_column,
            "weight",
        )
        self.assertColumnExists(pony_table, "weight")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnExists(pony_table, "weight")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_backwards(
                    app_label, editor, new_state, project_state
                )
        self.assertColumnExists(pony_table, "weight")

        rider_table = "%s_rider" % app_label
        new_state = project_state.clone()
        operation = migrations.AlterField(
            "Rider",
            "pony",
            models.ForeignKey("Pony", models.CASCADE, db_column="pony_id"),
        )
        operation.state_forwards(app_label, new_state)
        self.assertIsNone(
            project_state.models[app_label, "rider"].fields["pony"].db_column,
        )
        self.assertIs(
            new_state.models[app_label, "rider"].fields["pony"].db_column,
            "pony_id",
        )
        self.assertColumnExists(rider_table, "pony_id")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnExists(rider_table, "pony_id")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_forwards(app_label, editor, new_state, project_state)
        self.assertColumnExists(rider_table, "pony_id")

    @skipUnlessDBFeature("supports_comments")
    def test_alter_model_table_comment(self):
        app_label = "test_almotaco"
        project_state = self.set_up_test_model(app_label)
        pony_table = f"{app_label}_pony"
        # Add table comment.
        operation = migrations.AlterModelTableComment("Pony", "Custom pony comment")
        self.assertEqual(operation.describe(), "Alter Pony table comment")
        self.assertEqual(operation.migration_name_fragment, "alter_pony_table_comment")
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            new_state.models[app_label, "pony"].options["db_table_comment"],
            "Custom pony comment",
        )
        self.assertTableCommentNotExists(pony_table)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertTableComment(pony_table, "Custom pony comment")
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertTableCommentNotExists(pony_table)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelTableComment")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2], {"name": "Pony", "table_comment": "Custom pony comment"}
        )

    def test_alter_field_pk(self):
        """
        The AlterField operation on primary keys (things like PostgreSQL's
        SERIAL weirdness).
        """
        project_state = self.set_up_test_model("test_alflpk")
        # Test the state alteration
        operation = migrations.AlterField(
            "Pony", "id", models.IntegerField(primary_key=True)
        )
        new_state = project_state.clone()
        operation.state_forwards("test_alflpk", new_state)
        self.assertIsInstance(
            project_state.models["test_alflpk", "pony"].fields["id"],
            models.AutoField,
        )
        self.assertIsInstance(
            new_state.models["test_alflpk", "pony"].fields["id"],
            models.IntegerField,
        )
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alflpk", editor, project_state, new_state)
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_alflpk", editor, new_state, project_state
            )

    @skipUnlessDBFeature("supports_foreign_keys")
    def test_alter_field_pk_fk(self):
        """
        Tests the AlterField operation on primary keys changes any FKs pointing to it.
        """
        project_state = self.set_up_test_model("test_alflpkfk", related_model=True)
        project_state = self.apply_operations(
            "test_alflpkfk",
            project_state,
            [
                migrations.CreateModel(
                    "Stable",
                    fields=[
                        ("ponies", models.ManyToManyField("Pony")),
                    ],
                ),
                migrations.AddField(
                    "Pony",
                    "stables",
                    models.ManyToManyField("Stable"),
                ),
            ],
        )
        # Test the state alteration
        operation = migrations.AlterField(
            "Pony", "id", models.FloatField(primary_key=True)
        )
        new_state = project_state.clone()
        operation.state_forwards("test_alflpkfk", new_state)
        self.assertIsInstance(
            project_state.models["test_alflpkfk", "pony"].fields["id"],
            models.AutoField,
        )
        self.assertIsInstance(
            new_state.models["test_alflpkfk", "pony"].fields["id"],
            models.FloatField,
        )

        def assertIdTypeEqualsFkType():
            with connection.cursor() as cursor:
                id_type, id_null = [
                    (c.type_code, c.null_ok)
                    for c in connection.introspection.get_table_description(
                        cursor, "test_alflpkfk_pony"
                    )
                    if c.name == "id"
                ][0]
                fk_type, fk_null = [
                    (c.type_code, c.null_ok)
                    for c in connection.introspection.get_table_description(
                        cursor, "test_alflpkfk_rider"
                    )
                    if c.name == "pony_id"
                ][0]
                m2m_fk_type, m2m_fk_null = [
                    (c.type_code, c.null_ok)
                    for c in connection.introspection.get_table_description(
                        cursor,
                        "test_alflpkfk_pony_stables",
                    )
                    if c.name == "pony_id"
                ][0]
                remote_m2m_fk_type, remote_m2m_fk_null = [
                    (c.type_code, c.null_ok)
                    for c in connection.introspection.get_table_description(
                        cursor,
                        "test_alflpkfk_stable_ponies",
                    )
                    if c.name == "pony_id"
                ][0]
            self.assertEqual(id_type, fk_type)
            self.assertEqual(id_type, m2m_fk_type)
            self.assertEqual(id_type, remote_m2m_fk_type)
            self.assertEqual(id_null, fk_null)
            self.assertEqual(id_null, m2m_fk_null)
            self.assertEqual(id_null, remote_m2m_fk_null)

        assertIdTypeEqualsFkType()
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_alflpkfk", editor, project_state, new_state
            )
        assertIdTypeEqualsFkType()
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                "test_alflpkfk_pony_stables",
                ["pony_id"],
                ("test_alflpkfk_pony", "id"),
            )
            self.assertFKExists(
                "test_alflpkfk_stable_ponies",
                ["pony_id"],
                ("test_alflpkfk_pony", "id"),
            )
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_alflpkfk", editor, new_state, project_state
            )
        assertIdTypeEqualsFkType()
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                "test_alflpkfk_pony_stables",
                ["pony_id"],
                ("test_alflpkfk_pony", "id"),
            )
            self.assertFKExists(
                "test_alflpkfk_stable_ponies",
                ["pony_id"],
                ("test_alflpkfk_pony", "id"),
            )

    @skipUnlessDBFeature("supports_collation_on_charfield", "supports_foreign_keys")
    def test_alter_field_pk_fk_db_collation(self):
        """
        AlterField operation of db_collation on primary keys changes any FKs
        pointing to it.
        """
        collation = connection.features.test_collations.get("non_default")
        if not collation:
            self.skipTest("Language collations are not supported.")

        app_label = "test_alflpkfkdbc"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            [
                migrations.CreateModel(
                    "Pony",
                    [
                        ("id", models.CharField(primary_key=True, max_length=10)),
                    ],
                ),
                migrations.CreateModel(
                    "Rider",
                    [
                        ("pony", models.ForeignKey("Pony", models.CASCADE)),
                    ],
                ),
                migrations.CreateModel(
                    "Stable",
                    [
                        ("ponies", models.ManyToManyField("Pony")),
                    ],
                ),
            ],
        )
        # State alteration.
        operation = migrations.AlterField(
            "Pony",
            "id",
            models.CharField(
                primary_key=True,
                max_length=10,
                db_collation=collation,
            ),
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        # Database alteration.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertColumnCollation(f"{app_label}_pony", "id", collation)
        self.assertColumnCollation(f"{app_label}_rider", "pony_id", collation)
        self.assertColumnCollation(f"{app_label}_stable_ponies", "pony_id", collation)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)

    def test_alter_field_pk_mti_fk(self):
        app_label = "test_alflpkmtifk"
        project_state = self.set_up_test_model(app_label, mti_model=True)
        project_state = self.apply_operations(
            app_label,
            project_state,
            [
                migrations.CreateModel(
                    "ShetlandRider",
                    fields=[
                        (
                            "pony",
                            models.ForeignKey(
                                f"{app_label}.ShetlandPony", models.CASCADE
                            ),
                        ),
                    ],
                ),
            ],
        )
        operation = migrations.AlterField(
            "Pony",
            "id",
            models.BigAutoField(primary_key=True),
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertIsInstance(
            new_state.models[app_label, "pony"].fields["id"],
            models.BigAutoField,
        )

        def _get_column_id_type(cursor, table, column):
            return [
                c.type_code
                for c in connection.introspection.get_table_description(
                    cursor,
                    f"{app_label}_{table}",
                )
                if c.name == column
            ][0]

        def assertIdTypeEqualsMTIFkType():
            with connection.cursor() as cursor:
                parent_id_type = _get_column_id_type(cursor, "pony", "id")
                child_id_type = _get_column_id_type(
                    cursor, "shetlandpony", "pony_ptr_id"
                )
                mti_id_type = _get_column_id_type(cursor, "shetlandrider", "pony_id")
            self.assertEqual(parent_id_type, child_id_type)
            self.assertEqual(parent_id_type, mti_id_type)

        assertIdTypeEqualsMTIFkType()
        # Alter primary key.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        assertIdTypeEqualsMTIFkType()
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                f"{app_label}_shetlandpony",
                ["pony_ptr_id"],
                (f"{app_label}_pony", "id"),
            )
            self.assertFKExists(
                f"{app_label}_shetlandrider",
                ["pony_id"],
                (f"{app_label}_shetlandpony", "pony_ptr_id"),
            )
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        assertIdTypeEqualsMTIFkType()
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                f"{app_label}_shetlandpony",
                ["pony_ptr_id"],
                (f"{app_label}_pony", "id"),
            )
            self.assertFKExists(
                f"{app_label}_shetlandrider",
                ["pony_id"],
                (f"{app_label}_shetlandpony", "pony_ptr_id"),
            )

    def test_alter_field_pk_mti_and_fk_to_base(self):
        app_label = "test_alflpkmtiftb"
        project_state = self.set_up_test_model(
            app_label,
            mti_model=True,
            related_model=True,
        )
        operation = migrations.AlterField(
            "Pony",
            "id",
            models.BigAutoField(primary_key=True),
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertIsInstance(
            new_state.models[app_label, "pony"].fields["id"],
            models.BigAutoField,
        )

        def _get_column_id_type(cursor, table, column):
            return [
                c.type_code
                for c in connection.introspection.get_table_description(
                    cursor,
                    f"{app_label}_{table}",
                )
                if c.name == column
            ][0]

        def assertIdTypeEqualsMTIFkType():
            with connection.cursor() as cursor:
                parent_id_type = _get_column_id_type(cursor, "pony", "id")
                fk_id_type = _get_column_id_type(cursor, "rider", "pony_id")
                child_id_type = _get_column_id_type(
                    cursor, "shetlandpony", "pony_ptr_id"
                )
            self.assertEqual(parent_id_type, child_id_type)
            self.assertEqual(parent_id_type, fk_id_type)

        assertIdTypeEqualsMTIFkType()
        # Alter primary key.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        assertIdTypeEqualsMTIFkType()
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                f"{app_label}_shetlandpony",
                ["pony_ptr_id"],
                (f"{app_label}_pony", "id"),
            )
            self.assertFKExists(
                f"{app_label}_rider",
                ["pony_id"],
                (f"{app_label}_pony", "id"),
            )
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        assertIdTypeEqualsMTIFkType()
        if connection.features.supports_foreign_keys:
            self.assertFKExists(
                f"{app_label}_shetlandpony",
                ["pony_ptr_id"],
                (f"{app_label}_pony", "id"),
            )
            self.assertFKExists(
                f"{app_label}_rider",
                ["pony_id"],
                (f"{app_label}_pony", "id"),
            )

    @skipUnlessDBFeature("supports_foreign_keys")
    def test_alter_field_reloads_state_on_fk_with_to_field_target_type_change(self):
        app_label = "test_alflrsfkwtflttc"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("code", models.IntegerField(unique=True)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "rider",
                            models.ForeignKey(
                                "%s.Rider" % app_label, models.CASCADE, to_field="code"
                            ),
                        ),
                    ],
                ),
            ],
        )
        operation = migrations.AlterField(
            "Rider",
            "code",
            models.CharField(max_length=100, unique=True),
        )
        self.apply_operations(app_label, project_state, operations=[operation])
        id_type, id_null = [
            (c.type_code, c.null_ok)
            for c in self.get_table_description("%s_rider" % app_label)
            if c.name == "code"
        ][0]
        fk_type, fk_null = [
            (c.type_code, c.null_ok)
            for c in self.get_table_description("%s_pony" % app_label)
            if c.name == "rider_id"
        ][0]
        self.assertEqual(id_type, fk_type)
        self.assertEqual(id_null, fk_null)

    @skipUnlessDBFeature("supports_foreign_keys")
    def test_alter_field_reloads_state_fk_with_to_field_related_name_target_type_change(
        self,
    ):
        app_label = "test_alflrsfkwtflrnttc"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("code", models.PositiveIntegerField(unique=True)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "rider",
                            models.ForeignKey(
                                "%s.Rider" % app_label,
                                models.CASCADE,
                                to_field="code",
                                related_name="+",
                            ),
                        ),
                    ],
                ),
            ],
        )
        operation = migrations.AlterField(
            "Rider",
            "code",
            models.CharField(max_length=100, unique=True),
        )
        self.apply_operations(app_label, project_state, operations=[operation])

    def test_alter_field_reloads_state_on_fk_target_changes(self):
        """
        If AlterField doesn't reload state appropriately, the second AlterField
        crashes on MySQL due to not dropping the PonyRider.pony foreign key
        constraint before modifying the column.
        """
        app_label = "alter_alter_field_reloads_state_on_fk_target_changes"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.CharField(primary_key=True, max_length=100)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.CharField(primary_key=True, max_length=100)),
                        (
                            "rider",
                            models.ForeignKey("%s.Rider" % app_label, models.CASCADE),
                        ),
                    ],
                ),
                migrations.CreateModel(
                    "PonyRider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "pony",
                            models.ForeignKey("%s.Pony" % app_label, models.CASCADE),
                        ),
                    ],
                ),
            ],
        )
        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.AlterField(
                    "Rider", "id", models.CharField(primary_key=True, max_length=99)
                ),
                migrations.AlterField(
                    "Pony", "id", models.CharField(primary_key=True, max_length=99)
                ),
            ],
        )

    def test_alter_field_reloads_state_on_fk_with_to_field_target_changes(self):
        """
        If AlterField doesn't reload state appropriately, the second AlterField
        crashes on MySQL due to not dropping the PonyRider.pony foreign key
        constraint before modifying the column.
        """
        app_label = "alter_alter_field_reloads_state_on_fk_with_to_field_target_changes"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.CharField(primary_key=True, max_length=100)),
                        ("slug", models.CharField(unique=True, max_length=100)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.CharField(primary_key=True, max_length=100)),
                        (
                            "rider",
                            models.ForeignKey(
                                "%s.Rider" % app_label, models.CASCADE, to_field="slug"
                            ),
                        ),
                        ("slug", models.CharField(unique=True, max_length=100)),
                    ],
                ),
                migrations.CreateModel(
                    "PonyRider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "pony",
                            models.ForeignKey(
                                "%s.Pony" % app_label, models.CASCADE, to_field="slug"
                            ),
                        ),
                    ],
                ),
            ],
        )
        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.AlterField(
                    "Rider", "slug", models.CharField(unique=True, max_length=99)
                ),
                migrations.AlterField(
                    "Pony", "slug", models.CharField(unique=True, max_length=99)
                ),
            ],
        )

    def test_alter_field_pk_fk_char_to_int(self):
        app_label = "alter_field_pk_fk_char_to_int"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    name="Parent",
                    fields=[
                        ("id", models.CharField(max_length=255, primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    name="Child",
                    fields=[
                        ("id", models.BigAutoField(primary_key=True)),
                        (
                            "parent",
                            models.ForeignKey(
                                f"{app_label}.Parent",
                                on_delete=models.CASCADE,
                            ),
                        ),
                    ],
                ),
            ],
        )
        self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.AlterField(
                    model_name="parent",
                    name="id",
                    field=models.BigIntegerField(primary_key=True),
                ),
            ],
        )

    def test_rename_field_reloads_state_on_fk_target_changes(self):
        """
        If RenameField doesn't reload state appropriately, the AlterField
        crashes on MySQL due to not dropping the PonyRider.pony foreign key
        constraint before modifying the column.
        """
        app_label = "alter_rename_field_reloads_state_on_fk_target_changes"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Rider",
                    fields=[
                        ("id", models.CharField(primary_key=True, max_length=100)),
                    ],
                ),
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.CharField(primary_key=True, max_length=100)),
                        (
                            "rider",
                            models.ForeignKey("%s.Rider" % app_label, models.CASCADE),
                        ),
                    ],
                ),
                migrations.CreateModel(
                    "PonyRider",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "pony",
                            models.ForeignKey("%s.Pony" % app_label, models.CASCADE),
                        ),
                    ],
                ),
            ],
        )
        project_state = self.apply_operations(
            app_label,
            project_state,
            operations=[
                migrations.RenameField("Rider", "id", "id2"),
                migrations.AlterField(
                    "Pony", "id", models.CharField(primary_key=True, max_length=99)
                ),
            ],
            atomic=connection.features.supports_atomic_references_rename,
        )

    def test_rename_field(self):
        """
        Tests the RenameField operation.
        """
        project_state = self.set_up_test_model("test_rnfl")
        operation = migrations.RenameField("Pony", "pink", "blue")
        self.assertEqual(operation.describe(), "Rename field pink on Pony to blue")
        self.assertEqual(operation.migration_name_fragment, "rename_pink_pony_blue")
        new_state = project_state.clone()
        operation.state_forwards("test_rnfl", new_state)
        self.assertIn("blue", new_state.models["test_rnfl", "pony"].fields)
        self.assertNotIn("pink", new_state.models["test_rnfl", "pony"].fields)
        # Rename field.
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnfl", editor, project_state, new_state)
        self.assertColumnExists("test_rnfl_pony", "blue")
        self.assertColumnNotExists("test_rnfl_pony", "pink")
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rnfl", editor, new_state, project_state)
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RenameField")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"model_name": "Pony", "old_name": "pink", "new_name": "blue"},
        )

    def test_rename_field_unique_together(self):
        project_state = self.set_up_test_model("test_rnflut", unique_together=True)
        operation = migrations.RenameField("Pony", "pink", "blue")
        new_state = project_state.clone()
        operation.state_forwards("test_rnflut", new_state)
        # unique_together has the renamed column.
        self.assertIn(
            "blue",
            new_state.models["test_rnflut", "pony"].options["unique_together"][0],
        )
        self.assertNotIn(
            "pink",
            new_state.models["test_rnflut", "pony"].options["unique_together"][0],
        )
        # Rename field.
        self.assertColumnExists("test_rnflut_pony", "pink")
        self.assertColumnNotExists("test_rnflut_pony", "blue")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnflut", editor, project_state, new_state)
        self.assertColumnExists("test_rnflut_pony", "blue")
        self.assertColumnNotExists("test_rnflut_pony", "pink")
        # The unique constraint has been ported over.
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO test_rnflut_pony (blue, weight) VALUES (1, 1)")
            with self.assertRaises(IntegrityError):
                with atomic():
                    cursor.execute(
                        "INSERT INTO test_rnflut_pony (blue, weight) VALUES (1, 1)"
                    )
            cursor.execute("DELETE FROM test_rnflut_pony")
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_rnflut", editor, new_state, project_state
            )
        self.assertColumnExists("test_rnflut_pony", "pink")
        self.assertColumnNotExists("test_rnflut_pony", "blue")

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_rename_field_index_together(self):
        project_state = self.set_up_test_model("test_rnflit", index_together=True)
        operation = migrations.RenameField("Pony", "pink", "blue")
        new_state = project_state.clone()
        operation.state_forwards("test_rnflit", new_state)
        self.assertIn("blue", new_state.models["test_rnflit", "pony"].fields)
        self.assertNotIn("pink", new_state.models["test_rnflit", "pony"].fields)
        # index_together has the renamed column.
        self.assertIn(
            "blue", new_state.models["test_rnflit", "pony"].options["index_together"][0]
        )
        self.assertNotIn(
            "pink", new_state.models["test_rnflit", "pony"].options["index_together"][0]
        )
        # Rename field.
        self.assertColumnExists("test_rnflit_pony", "pink")
        self.assertColumnNotExists("test_rnflit_pony", "blue")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnflit", editor, project_state, new_state)
        self.assertColumnExists("test_rnflit_pony", "blue")
        self.assertColumnNotExists("test_rnflit_pony", "pink")
        # The index constraint has been ported over.
        self.assertIndexExists("test_rnflit_pony", ["weight", "blue"])
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_rnflit", editor, new_state, project_state
            )
        self.assertIndexExists("test_rnflit_pony", ["weight", "pink"])

    def test_rename_field_with_db_column(self):
        project_state = self.apply_operations(
            "test_rfwdbc",
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("field", models.IntegerField(db_column="db_field")),
                        (
                            "fk_field",
                            models.ForeignKey(
                                "Pony",
                                models.CASCADE,
                                db_column="db_fk_field",
                            ),
                        ),
                    ],
                ),
            ],
        )
        new_state = project_state.clone()
        operation = migrations.RenameField("Pony", "field", "renamed_field")
        operation.state_forwards("test_rfwdbc", new_state)
        self.assertIn("renamed_field", new_state.models["test_rfwdbc", "pony"].fields)
        self.assertNotIn("field", new_state.models["test_rfwdbc", "pony"].fields)
        self.assertColumnExists("test_rfwdbc_pony", "db_field")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_forwards(
                    "test_rfwdbc", editor, project_state, new_state
                )
        self.assertColumnExists("test_rfwdbc_pony", "db_field")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_backwards(
                    "test_rfwdbc", editor, new_state, project_state
                )
        self.assertColumnExists("test_rfwdbc_pony", "db_field")

        new_state = project_state.clone()
        operation = migrations.RenameField("Pony", "fk_field", "renamed_fk_field")
        operation.state_forwards("test_rfwdbc", new_state)
        self.assertIn(
            "renamed_fk_field", new_state.models["test_rfwdbc", "pony"].fields
        )
        self.assertNotIn("fk_field", new_state.models["test_rfwdbc", "pony"].fields)
        self.assertColumnExists("test_rfwdbc_pony", "db_fk_field")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_forwards(
                    "test_rfwdbc", editor, project_state, new_state
                )
        self.assertColumnExists("test_rfwdbc_pony", "db_fk_field")
        with connection.schema_editor() as editor:
            with self.assertNumQueries(0):
                operation.database_backwards(
                    "test_rfwdbc", editor, new_state, project_state
                )
        self.assertColumnExists("test_rfwdbc_pony", "db_fk_field")

    def test_rename_field_case(self):
        project_state = self.apply_operations(
            "test_rfmx",
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("field", models.IntegerField()),
                    ],
                ),
            ],
        )
        new_state = project_state.clone()
        operation = migrations.RenameField("Pony", "field", "FiElD")
        operation.state_forwards("test_rfmx", new_state)
        self.assertIn("FiElD", new_state.models["test_rfmx", "pony"].fields)
        self.assertColumnExists("test_rfmx_pony", "field")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rfmx", editor, project_state, new_state)
        self.assertColumnExists(
            "test_rfmx_pony",
            connection.introspection.identifier_converter("FiElD"),
        )
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rfmx", editor, new_state, project_state)
        self.assertColumnExists("test_rfmx_pony", "field")

    def test_rename_missing_field(self):
        state = ProjectState()
        state.add_model(ModelState("app", "model", []))
        with self.assertRaisesMessage(
            FieldDoesNotExist, "app.model has no field named 'field'"
        ):
            migrations.RenameField("model", "field", "new_field").state_forwards(
                "app", state
            )

    def test_rename_referenced_field_state_forward(self):
        state = ProjectState()
        state.add_model(
            ModelState(
                "app",
                "Model",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field", models.IntegerField(unique=True)),
                ],
            )
        )
        state.add_model(
            ModelState(
                "app",
                "OtherModel",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "fk",
                        models.ForeignKey("Model", models.CASCADE, to_field="field"),
                    ),
                    (
                        "fo",
                        models.ForeignObject(
                            "Model",
                            models.CASCADE,
                            from_fields=("fk",),
                            to_fields=("field",),
                        ),
                    ),
                ],
            )
        )
        operation = migrations.RenameField("Model", "field", "renamed")
        new_state = state.clone()
        operation.state_forwards("app", new_state)
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fk"].remote_field.field_name,
            "renamed",
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fk"].from_fields, ["self"]
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fk"].to_fields, ("renamed",)
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fo"].from_fields, ("fk",)
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fo"].to_fields, ("renamed",)
        )
        operation = migrations.RenameField("OtherModel", "fk", "renamed_fk")
        new_state = state.clone()
        operation.state_forwards("app", new_state)
        self.assertEqual(
            new_state.models["app", "othermodel"]
            .fields["renamed_fk"]
            .remote_field.field_name,
            "renamed",
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["renamed_fk"].from_fields,
            ("self",),
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["renamed_fk"].to_fields,
            ("renamed",),
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fo"].from_fields,
            ("renamed_fk",),
        )
        self.assertEqual(
            new_state.models["app", "othermodel"].fields["fo"].to_fields, ("renamed",)
        )

    def test_alter_unique_together(self):
        """
        Tests the AlterUniqueTogether operation.
        """
        project_state = self.set_up_test_model("test_alunto")
        # Test the state alteration
        operation = migrations.AlterUniqueTogether("Pony", [("pink", "weight")])
        self.assertEqual(
            operation.describe(), "Alter unique_together for Pony (1 constraint(s))"
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "alter_pony_unique_together",
        )
        new_state = project_state.clone()
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(
            len(
                project_state.models["test_alunto", "pony"].options.get(
                    "unique_together", set()
                )
            ),
            0,
        )
        self.assertEqual(
            len(
                new_state.models["test_alunto", "pony"].options.get(
                    "unique_together", set()
                )
            ),
            1,
        )
        # Make sure we can insert duplicate rows
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
            # Test the database alteration
            with connection.schema_editor() as editor:
                operation.database_forwards(
                    "test_alunto", editor, project_state, new_state
                )
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            with self.assertRaises(IntegrityError):
                with atomic():
                    cursor.execute(
                        "INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)"
                    )
            cursor.execute("DELETE FROM test_alunto_pony")
            # And test reversal
            with connection.schema_editor() as editor:
                operation.database_backwards(
                    "test_alunto", editor, new_state, project_state
                )
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
        # Test flat unique_together
        operation = migrations.AlterUniqueTogether("Pony", ("pink", "weight"))
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(
            len(
                new_state.models["test_alunto", "pony"].options.get(
                    "unique_together", set()
                )
            ),
            1,
        )
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterUniqueTogether")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2], {"name": "Pony", "unique_together": {("pink", "weight")}}
        )

    def test_alter_unique_together_remove(self):
        operation = migrations.AlterUniqueTogether("Pony", None)
        self.assertEqual(
            operation.describe(), "Alter unique_together for Pony (0 constraint(s))"
        )

    @skipUnlessDBFeature("allows_multiple_constraints_on_same_fields")
    def test_remove_unique_together_on_pk_field(self):
        app_label = "test_rutopkf"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Pony",
                    fields=[("id", models.AutoField(primary_key=True))],
                    options={"unique_together": {("id",)}},
                ),
            ],
        )
        table_name = f"{app_label}_pony"
        pk_constraint_name = f"{table_name}_pkey"
        unique_together_constraint_name = f"{table_name}_id_fb61f881_uniq"
        self.assertConstraintExists(table_name, pk_constraint_name, value=False)
        self.assertConstraintExists(
            table_name, unique_together_constraint_name, value=False
        )

        new_state = project_state.clone()
        operation = migrations.AlterUniqueTogether("Pony", set())
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertConstraintExists(table_name, pk_constraint_name, value=False)
        self.assertConstraintNotExists(table_name, unique_together_constraint_name)

    @skipUnlessDBFeature("allows_multiple_constraints_on_same_fields")
    def test_remove_unique_together_on_unique_field(self):
        app_label = "test_rutouf"
        project_state = self.apply_operations(
            app_label,
            ProjectState(),
            operations=[
                migrations.CreateModel(
                    "Pony",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=30, unique=True)),
                    ],
                    options={"unique_together": {("name",)}},
                ),
            ],
        )
        table_name = f"{app_label}_pony"
        unique_constraint_name = f"{table_name}_name_key"
        unique_together_constraint_name = f"{table_name}_name_694f3b9f_uniq"
        self.assertConstraintExists(table_name, unique_constraint_name, value=False)
        self.assertConstraintExists(
            table_name, unique_together_constraint_name, value=False
        )

        new_state = project_state.clone()
        operation = migrations.AlterUniqueTogether("Pony", set())
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertConstraintExists(table_name, unique_constraint_name, value=False)
        self.assertConstraintNotExists(table_name, unique_together_constraint_name)

    def test_add_index(self):
        """
        Test the AddIndex operation.
        """
        project_state = self.set_up_test_model("test_adin")
        msg = (
            "Indexes passed to AddIndex operations require a name argument. "
            "<Index: fields=['pink']> doesn't have one."
        )
        with self.assertRaisesMessage(ValueError, msg):
            migrations.AddIndex("Pony", models.Index(fields=["pink"]))
        index = models.Index(fields=["pink"], name="test_adin_pony_pink_idx")
        operation = migrations.AddIndex("Pony", index)
        self.assertEqual(
            operation.describe(),
            "Create index test_adin_pony_pink_idx on field(s) pink of model Pony",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "pony_test_adin_pony_pink_idx",
        )
        new_state = project_state.clone()
        operation.state_forwards("test_adin", new_state)
        # Test the database alteration
        self.assertEqual(
            len(new_state.models["test_adin", "pony"].options["indexes"]), 1
        )
        self.assertIndexNotExists("test_adin_pony", ["pink"])
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adin", editor, project_state, new_state)
        self.assertIndexExists("test_adin_pony", ["pink"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adin", editor, new_state, project_state)
        self.assertIndexNotExists("test_adin_pony", ["pink"])
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddIndex")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Pony", "index": index})

    def test_remove_index(self):
        """
        Test the RemoveIndex operation.
        """
        project_state = self.set_up_test_model("test_rmin", multicol_index=True)
        self.assertTableExists("test_rmin_pony")
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])
        operation = migrations.RemoveIndex("Pony", "pony_test_idx")
        self.assertEqual(operation.describe(), "Remove index pony_test_idx from Pony")
        self.assertEqual(
            operation.migration_name_fragment,
            "remove_pony_pony_test_idx",
        )
        new_state = project_state.clone()
        operation.state_forwards("test_rmin", new_state)
        # Test the state alteration
        self.assertEqual(
            len(new_state.models["test_rmin", "pony"].options["indexes"]), 0
        )
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rmin", editor, project_state, new_state)
        self.assertIndexNotExists("test_rmin_pony", ["pink", "weight"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rmin", editor, new_state, project_state)
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveIndex")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Pony", "name": "pony_test_idx"})

        # Also test a field dropped with index - sqlite remake issue
        operations = [
            migrations.RemoveIndex("Pony", "pony_test_idx"),
            migrations.RemoveField("Pony", "pink"),
        ]
        self.assertColumnExists("test_rmin_pony", "pink")
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])
        # Test database alteration
        new_state = project_state.clone()
        self.apply_operations("test_rmin", new_state, operations=operations)
        self.assertColumnNotExists("test_rmin_pony", "pink")
        self.assertIndexNotExists("test_rmin_pony", ["pink", "weight"])
        # And test reversal
        self.unapply_operations("test_rmin", project_state, operations=operations)
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])

    def test_rename_index(self):
        app_label = "test_rnin"
        project_state = self.set_up_test_model(app_label, index=True)
        table_name = app_label + "_pony"
        self.assertIndexNameExists(table_name, "pony_pink_idx")
        self.assertIndexNameNotExists(table_name, "new_pony_test_idx")
        operation = migrations.RenameIndex(
            "Pony", new_name="new_pony_test_idx", old_name="pony_pink_idx"
        )
        self.assertEqual(
            operation.describe(),
            "Rename index pony_pink_idx on Pony to new_pony_test_idx",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "rename_pony_pink_idx_new_pony_test_idx",
        )

        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        # Rename index.
        expected_queries = 1 if connection.features.can_rename_index else 2
        with connection.schema_editor() as editor, self.assertNumQueries(
            expected_queries
        ):
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNameNotExists(table_name, "pony_pink_idx")
        self.assertIndexNameExists(table_name, "new_pony_test_idx")
        # Reversal.
        with connection.schema_editor() as editor, self.assertNumQueries(
            expected_queries
        ):
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertIndexNameExists(table_name, "pony_pink_idx")
        self.assertIndexNameNotExists(table_name, "new_pony_test_idx")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RenameIndex")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "model_name": "Pony",
                "old_name": "pony_pink_idx",
                "new_name": "new_pony_test_idx",
            },
        )

    def test_rename_index_arguments(self):
        msg = "RenameIndex.old_name and old_fields are mutually exclusive."
        with self.assertRaisesMessage(ValueError, msg):
            migrations.RenameIndex(
                "Pony",
                new_name="new_idx_name",
                old_name="old_idx_name",
                old_fields=("weight", "pink"),
            )
        msg = "RenameIndex requires one of old_name and old_fields arguments to be set."
        with self.assertRaisesMessage(ValueError, msg):
            migrations.RenameIndex("Pony", new_name="new_idx_name")

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_rename_index_unnamed_index(self):
        app_label = "test_rninui"
        project_state = self.set_up_test_model(app_label, index_together=True)
        table_name = app_label + "_pony"
        self.assertIndexNameNotExists(table_name, "new_pony_test_idx")
        operation = migrations.RenameIndex(
            "Pony", new_name="new_pony_test_idx", old_fields=("weight", "pink")
        )
        self.assertEqual(
            operation.describe(),
            "Rename unnamed index for ('weight', 'pink') on Pony to new_pony_test_idx",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "rename_pony_weight_pink_new_pony_test_idx",
        )

        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        # Rename index.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNameExists(table_name, "new_pony_test_idx")
        # Reverse is a no-op.
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertIndexNameExists(table_name, "new_pony_test_idx")
        # Reapply, RenameIndex operation is a noop when the old and new name
        # match.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, new_state, project_state)
        self.assertIndexNameExists(table_name, "new_pony_test_idx")
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RenameIndex")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "model_name": "Pony",
                "new_name": "new_pony_test_idx",
                "old_fields": ("weight", "pink"),
            },
        )

    def test_rename_index_unknown_unnamed_index(self):
        app_label = "test_rninuui"
        project_state = self.set_up_test_model(app_label)
        operation = migrations.RenameIndex(
            "Pony", new_name="new_pony_test_idx", old_fields=("weight", "pink")
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        msg = "Found wrong number (0) of indexes for test_rninuui_pony(weight, pink)."
        with connection.schema_editor() as editor:
            with self.assertRaisesMessage(ValueError, msg):
                operation.database_forwards(app_label, editor, project_state, new_state)

    def test_add_index_state_forwards(self):
        project_state = self.set_up_test_model("test_adinsf")
        index = models.Index(fields=["pink"], name="test_adinsf_pony_pink_idx")
        old_model = project_state.apps.get_model("test_adinsf", "Pony")
        new_state = project_state.clone()

        operation = migrations.AddIndex("Pony", index)
        operation.state_forwards("test_adinsf", new_state)
        new_model = new_state.apps.get_model("test_adinsf", "Pony")
        self.assertIsNot(old_model, new_model)

    def test_remove_index_state_forwards(self):
        project_state = self.set_up_test_model("test_rminsf")
        index = models.Index(fields=["pink"], name="test_rminsf_pony_pink_idx")
        migrations.AddIndex("Pony", index).state_forwards("test_rminsf", project_state)
        old_model = project_state.apps.get_model("test_rminsf", "Pony")
        new_state = project_state.clone()

        operation = migrations.RemoveIndex("Pony", "test_rminsf_pony_pink_idx")
        operation.state_forwards("test_rminsf", new_state)
        new_model = new_state.apps.get_model("test_rminsf", "Pony")
        self.assertIsNot(old_model, new_model)

    def test_rename_index_state_forwards(self):
        app_label = "test_rnidsf"
        project_state = self.set_up_test_model(app_label, index=True)
        old_model = project_state.apps.get_model(app_label, "Pony")
        new_state = project_state.clone()

        operation = migrations.RenameIndex(
            "Pony", new_name="new_pony_pink_idx", old_name="pony_pink_idx"
        )
        operation.state_forwards(app_label, new_state)
        new_model = new_state.apps.get_model(app_label, "Pony")
        self.assertIsNot(old_model, new_model)
        self.assertEqual(new_model._meta.indexes[0].name, "new_pony_pink_idx")

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_rename_index_state_forwards_unnamed_index(self):
        app_label = "test_rnidsfui"
        project_state = self.set_up_test_model(app_label, index_together=True)
        old_model = project_state.apps.get_model(app_label, "Pony")
        new_state = project_state.clone()

        operation = migrations.RenameIndex(
            "Pony", new_name="new_pony_pink_idx", old_fields=("weight", "pink")
        )
        operation.state_forwards(app_label, new_state)
        new_model = new_state.apps.get_model(app_label, "Pony")
        self.assertIsNot(old_model, new_model)
        self.assertEqual(new_model._meta.index_together, tuple())
        self.assertEqual(new_model._meta.indexes[0].name, "new_pony_pink_idx")

    @skipUnlessDBFeature("supports_expression_indexes")
    def test_add_func_index(self):
        app_label = "test_addfuncin"
        index_name = f"{app_label}_pony_abs_idx"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        index = models.Index(Abs("weight"), name=index_name)
        operation = migrations.AddIndex("Pony", index)
        self.assertEqual(
            operation.describe(),
            "Create index test_addfuncin_pony_abs_idx on Abs(F(weight)) on model Pony",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "pony_test_addfuncin_pony_abs_idx",
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, "pony"].options["indexes"]), 1)
        self.assertIndexNameNotExists(table_name, index_name)
        # Add index.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNameExists(table_name, index_name)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertIndexNameNotExists(table_name, index_name)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddIndex")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Pony", "index": index})

    @skipUnlessDBFeature("supports_expression_indexes")
    def test_remove_func_index(self):
        app_label = "test_rmfuncin"
        index_name = f"{app_label}_pony_abs_idx"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(
            app_label,
            indexes=[
                models.Index(Abs("weight"), name=index_name),
            ],
        )
        self.assertTableExists(table_name)
        self.assertIndexNameExists(table_name, index_name)
        operation = migrations.RemoveIndex("Pony", index_name)
        self.assertEqual(
            operation.describe(),
            "Remove index test_rmfuncin_pony_abs_idx from Pony",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "remove_pony_test_rmfuncin_pony_abs_idx",
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, "pony"].options["indexes"]), 0)
        # Remove index.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNameNotExists(table_name, index_name)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertIndexNameExists(table_name, index_name)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveIndex")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Pony", "name": index_name})

    @skipUnlessDBFeature("supports_expression_indexes")
    def test_alter_field_with_func_index(self):
        app_label = "test_alfuncin"
        index_name = f"{app_label}_pony_idx"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(
            app_label,
            indexes=[models.Index(Abs("pink"), name=index_name)],
        )
        operation = migrations.AlterField(
            "Pony", "pink", models.IntegerField(null=True)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNameExists(table_name, index_name)
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertIndexNameExists(table_name, index_name)

    def test_alter_field_with_index(self):
        """
        Test AlterField operation with an index to ensure indexes created via
        Meta.indexes don't get dropped with sqlite3 remake.
        """
        project_state = self.set_up_test_model("test_alflin", index=True)
        operation = migrations.AlterField(
            "Pony", "pink", models.IntegerField(null=True)
        )
        new_state = project_state.clone()
        operation.state_forwards("test_alflin", new_state)
        # Test the database alteration
        self.assertColumnNotNull("test_alflin_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alflin", editor, project_state, new_state)
        # Index hasn't been dropped
        self.assertIndexExists("test_alflin_pony", ["pink"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_alflin", editor, new_state, project_state
            )
        # Ensure the index is still there
        self.assertIndexExists("test_alflin_pony", ["pink"])

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_alter_index_together(self):
        """
        Tests the AlterIndexTogether operation.
        """
        project_state = self.set_up_test_model("test_alinto")
        # Test the state alteration
        operation = migrations.AlterIndexTogether("Pony", [("pink", "weight")])
        self.assertEqual(
            operation.describe(), "Alter index_together for Pony (1 constraint(s))"
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "alter_pony_index_together",
        )
        new_state = project_state.clone()
        operation.state_forwards("test_alinto", new_state)
        self.assertEqual(
            len(
                project_state.models["test_alinto", "pony"].options.get(
                    "index_together", set()
                )
            ),
            0,
        )
        self.assertEqual(
            len(
                new_state.models["test_alinto", "pony"].options.get(
                    "index_together", set()
                )
            ),
            1,
        )
        # Make sure there's no matching index
        self.assertIndexNotExists("test_alinto_pony", ["pink", "weight"])
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alinto", editor, project_state, new_state)
        self.assertIndexExists("test_alinto_pony", ["pink", "weight"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_alinto", editor, new_state, project_state
            )
        self.assertIndexNotExists("test_alinto_pony", ["pink", "weight"])
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterIndexTogether")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2], {"name": "Pony", "index_together": {("pink", "weight")}}
        )

    def test_alter_index_together_remove(self):
        operation = migrations.AlterIndexTogether("Pony", None)
        self.assertEqual(
            operation.describe(), "Alter index_together for Pony (0 constraint(s))"
        )

    @skipUnlessDBFeature("allows_multiple_constraints_on_same_fields")
    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_alter_index_together_remove_with_unique_together(self):
        app_label = "test_alintoremove_wunto"
        table_name = "%s_pony" % app_label
        project_state = self.set_up_test_model(app_label, unique_together=True)
        self.assertUniqueConstraintExists(table_name, ["pink", "weight"])
        # Add index together.
        new_state = project_state.clone()
        operation = migrations.AlterIndexTogether("Pony", [("pink", "weight")])
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexExists(table_name, ["pink", "weight"])
        # Remove index together.
        project_state = new_state
        new_state = project_state.clone()
        operation = migrations.AlterIndexTogether("Pony", set())
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNotExists(table_name, ["pink", "weight"])
        self.assertUniqueConstraintExists(table_name, ["pink", "weight"])

    def test_add_constraint(self):
        project_state = self.set_up_test_model("test_addconstraint")
        gt_check = models.Q(pink__gt=2)
        gt_constraint = models.CheckConstraint(
            check=gt_check, name="test_add_constraint_pony_pink_gt_2"
        )
        gt_operation = migrations.AddConstraint("Pony", gt_constraint)
        self.assertEqual(
            gt_operation.describe(),
            "Create constraint test_add_constraint_pony_pink_gt_2 on model Pony",
        )
        self.assertEqual(
            gt_operation.migration_name_fragment,
            "pony_test_add_constraint_pony_pink_gt_2",
        )
        # Test the state alteration
        new_state = project_state.clone()
        gt_operation.state_forwards("test_addconstraint", new_state)
        self.assertEqual(
            len(new_state.models["test_addconstraint", "pony"].options["constraints"]),
            1,
        )
        Pony = new_state.apps.get_model("test_addconstraint", "Pony")
        self.assertEqual(len(Pony._meta.constraints), 1)
        # Test the database alteration
        with (
            CaptureQueriesContext(connection) as ctx,
            connection.schema_editor() as editor,
        ):
            gt_operation.database_forwards(
                "test_addconstraint", editor, project_state, new_state
            )
        if connection.features.supports_table_check_constraints:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Pony.objects.create(pink=1, weight=1.0)
        else:
            self.assertIs(
                any("CHECK" in query["sql"] for query in ctx.captured_queries), False
            )
            Pony.objects.create(pink=1, weight=1.0)
        # Add another one.
        lt_check = models.Q(pink__lt=100)
        lt_constraint = models.CheckConstraint(
            check=lt_check, name="test_add_constraint_pony_pink_lt_100"
        )
        lt_operation = migrations.AddConstraint("Pony", lt_constraint)
        lt_operation.state_forwards("test_addconstraint", new_state)
        self.assertEqual(
            len(new_state.models["test_addconstraint", "pony"].options["constraints"]),
            2,
        )
        Pony = new_state.apps.get_model("test_addconstraint", "Pony")
        self.assertEqual(len(Pony._meta.constraints), 2)
        with (
            CaptureQueriesContext(connection) as ctx,
            connection.schema_editor() as editor,
        ):
            lt_operation.database_forwards(
                "test_addconstraint", editor, project_state, new_state
            )
        if connection.features.supports_table_check_constraints:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Pony.objects.create(pink=100, weight=1.0)
        else:
            self.assertIs(
                any("CHECK" in query["sql"] for query in ctx.captured_queries), False
            )
            Pony.objects.create(pink=100, weight=1.0)
        # Test reversal
        with connection.schema_editor() as editor:
            gt_operation.database_backwards(
                "test_addconstraint", editor, new_state, project_state
            )
        Pony.objects.create(pink=1, weight=1.0)
        # Test deconstruction
        definition = gt_operation.deconstruct()
        self.assertEqual(definition[0], "AddConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2], {"model_name": "Pony", "constraint": gt_constraint}
        )

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_add_constraint_percent_escaping(self):
        app_label = "add_constraint_string_quoting"
        operations = [
            migrations.CreateModel(
                "Author",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("surname", models.CharField(max_length=100, default="")),
                    ("rebate", models.CharField(max_length=100)),
                ],
            ),
        ]
        from_state = self.apply_operations(app_label, ProjectState(), operations)
        checks = [
            # "%" generated in startswith lookup should be escaped in a way
            # that is considered a leading wildcard.
            (
                models.Q(name__startswith="Albert"),
                {"name": "Alberta"},
                {"name": "Artur"},
            ),
            # Literal "%" should be escaped in a way that is not a considered a
            # wildcard.
            (models.Q(rebate__endswith="%"), {"rebate": "10%"}, {"rebate": "10%$"}),
            # Right-hand-side baked "%" literals should not be used for
            # parameters interpolation.
            (
                ~models.Q(surname__startswith=models.F("name")),
                {"name": "Albert"},
                {"name": "Albert", "surname": "Alberto"},
            ),
            # Exact matches against "%" literals should also be supported.
            (
                models.Q(name="%"),
                {"name": "%"},
                {"name": "Albert"},
            ),
        ]
        for check, valid, invalid in checks:
            with self.subTest(check=check, valid=valid, invalid=invalid):
                constraint = models.CheckConstraint(check=check, name="constraint")
                operation = migrations.AddConstraint("Author", constraint)
                to_state = from_state.clone()
                operation.state_forwards(app_label, to_state)
                with connection.schema_editor() as editor:
                    operation.database_forwards(app_label, editor, from_state, to_state)
                Author = to_state.apps.get_model(app_label, "Author")
                try:
                    with transaction.atomic():
                        Author.objects.create(**valid).delete()
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        Author.objects.create(**invalid)
                finally:
                    with connection.schema_editor() as editor:
                        operation.database_backwards(
                            app_label, editor, from_state, to_state
                        )

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_add_or_constraint(self):
        app_label = "test_addorconstraint"
        constraint_name = "add_constraint_or"
        from_state = self.set_up_test_model(app_label)
        check = models.Q(pink__gt=2, weight__gt=2) | models.Q(weight__lt=0)
        constraint = models.CheckConstraint(check=check, name=constraint_name)
        operation = migrations.AddConstraint("Pony", constraint)
        to_state = from_state.clone()
        operation.state_forwards(app_label, to_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, from_state, to_state)
        Pony = to_state.apps.get_model(app_label, "Pony")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pony.objects.create(pink=2, weight=3.0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pony.objects.create(pink=3, weight=1.0)
        Pony.objects.bulk_create(
            [
                Pony(pink=3, weight=-1.0),
                Pony(pink=1, weight=-1.0),
                Pony(pink=3, weight=3.0),
            ]
        )

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_add_constraint_combinable(self):
        app_label = "test_addconstraint_combinable"
        operations = [
            migrations.CreateModel(
                "Book",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("read", models.PositiveIntegerField()),
                    ("unread", models.PositiveIntegerField()),
                ],
            ),
        ]
        from_state = self.apply_operations(app_label, ProjectState(), operations)
        constraint = models.CheckConstraint(
            check=models.Q(read=(100 - models.F("unread"))),
            name="test_addconstraint_combinable_sum_100",
        )
        operation = migrations.AddConstraint("Book", constraint)
        to_state = from_state.clone()
        operation.state_forwards(app_label, to_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, from_state, to_state)
        Book = to_state.apps.get_model(app_label, "Book")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Book.objects.create(read=70, unread=10)
        Book.objects.create(read=70, unread=30)

    def test_remove_constraint(self):
        project_state = self.set_up_test_model(
            "test_removeconstraint",
            constraints=[
                models.CheckConstraint(
                    check=models.Q(pink__gt=2),
                    name="test_remove_constraint_pony_pink_gt_2",
                ),
                models.CheckConstraint(
                    check=models.Q(pink__lt=100),
                    name="test_remove_constraint_pony_pink_lt_100",
                ),
            ],
        )
        gt_operation = migrations.RemoveConstraint(
            "Pony", "test_remove_constraint_pony_pink_gt_2"
        )
        self.assertEqual(
            gt_operation.describe(),
            "Remove constraint test_remove_constraint_pony_pink_gt_2 from model Pony",
        )
        self.assertEqual(
            gt_operation.migration_name_fragment,
            "remove_pony_test_remove_constraint_pony_pink_gt_2",
        )
        # Test state alteration
        new_state = project_state.clone()
        gt_operation.state_forwards("test_removeconstraint", new_state)
        self.assertEqual(
            len(
                new_state.models["test_removeconstraint", "pony"].options["constraints"]
            ),
            1,
        )
        Pony = new_state.apps.get_model("test_removeconstraint", "Pony")
        self.assertEqual(len(Pony._meta.constraints), 1)
        # Test database alteration
        with connection.schema_editor() as editor:
            gt_operation.database_forwards(
                "test_removeconstraint", editor, project_state, new_state
            )
        Pony.objects.create(pink=1, weight=1.0).delete()
        if connection.features.supports_table_check_constraints:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Pony.objects.create(pink=100, weight=1.0)
        else:
            Pony.objects.create(pink=100, weight=1.0)
        # Remove the other one.
        lt_operation = migrations.RemoveConstraint(
            "Pony", "test_remove_constraint_pony_pink_lt_100"
        )
        lt_operation.state_forwards("test_removeconstraint", new_state)
        self.assertEqual(
            len(
                new_state.models["test_removeconstraint", "pony"].options["constraints"]
            ),
            0,
        )
        Pony = new_state.apps.get_model("test_removeconstraint", "Pony")
        self.assertEqual(len(Pony._meta.constraints), 0)
        with connection.schema_editor() as editor:
            lt_operation.database_forwards(
                "test_removeconstraint", editor, project_state, new_state
            )
        Pony.objects.create(pink=100, weight=1.0).delete()
        # Test reversal
        with connection.schema_editor() as editor:
            gt_operation.database_backwards(
                "test_removeconstraint", editor, new_state, project_state
            )
        if connection.features.supports_table_check_constraints:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Pony.objects.create(pink=1, weight=1.0)
        else:
            Pony.objects.create(pink=1, weight=1.0)
        # Test deconstruction
        definition = gt_operation.deconstruct()
        self.assertEqual(definition[0], "RemoveConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"model_name": "Pony", "name": "test_remove_constraint_pony_pink_gt_2"},
        )

    def test_add_partial_unique_constraint(self):
        project_state = self.set_up_test_model("test_addpartialuniqueconstraint")
        partial_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            condition=models.Q(weight__gt=5),
            name="test_constraint_pony_pink_for_weight_gt_5_uniq",
        )
        operation = migrations.AddConstraint("Pony", partial_unique_constraint)
        self.assertEqual(
            operation.describe(),
            "Create constraint test_constraint_pony_pink_for_weight_gt_5_uniq "
            "on model Pony",
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_addpartialuniqueconstraint", new_state)
        self.assertEqual(
            len(
                new_state.models["test_addpartialuniqueconstraint", "pony"].options[
                    "constraints"
                ]
            ),
            1,
        )
        Pony = new_state.apps.get_model("test_addpartialuniqueconstraint", "Pony")
        self.assertEqual(len(Pony._meta.constraints), 1)
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_addpartialuniqueconstraint", editor, project_state, new_state
            )
        # Test constraint works
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=6.0)
        if connection.features.supports_partial_indexes:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Pony.objects.create(pink=1, weight=7.0)
        else:
            Pony.objects.create(pink=1, weight=7.0)
        # Test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_addpartialuniqueconstraint", editor, new_state, project_state
            )
        # Test constraint doesn't work
        Pony.objects.create(pink=1, weight=7.0)
        # Test deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"model_name": "Pony", "constraint": partial_unique_constraint},
        )

    def test_remove_partial_unique_constraint(self):
        project_state = self.set_up_test_model(
            "test_removepartialuniqueconstraint",
            constraints=[
                models.UniqueConstraint(
                    fields=["pink"],
                    condition=models.Q(weight__gt=5),
                    name="test_constraint_pony_pink_for_weight_gt_5_uniq",
                ),
            ],
        )
        gt_operation = migrations.RemoveConstraint(
            "Pony", "test_constraint_pony_pink_for_weight_gt_5_uniq"
        )
        self.assertEqual(
            gt_operation.describe(),
            "Remove constraint test_constraint_pony_pink_for_weight_gt_5_uniq from "
            "model Pony",
        )
        # Test state alteration
        new_state = project_state.clone()
        gt_operation.state_forwards("test_removepartialuniqueconstraint", new_state)
        self.assertEqual(
            len(
                new_state.models["test_removepartialuniqueconstraint", "pony"].options[
                    "constraints"
                ]
            ),
            0,
        )
        Pony = new_state.apps.get_model("test_removepartialuniqueconstraint", "Pony")
        self.assertEqual(len(Pony._meta.constraints), 0)
        # Test database alteration
        with connection.schema_editor() as editor:
            gt_operation.database_forwards(
                "test_removepartialuniqueconstraint", editor, project_state, new_state
            )
        # Test constraint doesn't work
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=6.0)
        Pony.objects.create(pink=1, weight=7.0).delete()
        # Test reversal
        with connection.schema_editor() as editor:
            gt_operation.database_backwards(
                "test_removepartialuniqueconstraint", editor, new_state, project_state
            )
        # Test constraint works
        if connection.features.supports_partial_indexes:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Pony.objects.create(pink=1, weight=7.0)
        else:
            Pony.objects.create(pink=1, weight=7.0)
        # Test deconstruction
        definition = gt_operation.deconstruct()
        self.assertEqual(definition[0], "RemoveConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "model_name": "Pony",
                "name": "test_constraint_pony_pink_for_weight_gt_5_uniq",
            },
        )

    def test_add_deferred_unique_constraint(self):
        app_label = "test_adddeferred_uc"
        project_state = self.set_up_test_model(app_label)
        deferred_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            name="deferred_pink_constraint_add",
            deferrable=models.Deferrable.DEFERRED,
        )
        operation = migrations.AddConstraint("Pony", deferred_unique_constraint)
        self.assertEqual(
            operation.describe(),
            "Create constraint deferred_pink_constraint_add on model Pony",
        )
        # Add constraint.
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            len(new_state.models[app_label, "pony"].options["constraints"]), 1
        )
        Pony = new_state.apps.get_model(app_label, "Pony")
        self.assertEqual(len(Pony._meta.constraints), 1)
        with connection.schema_editor() as editor, CaptureQueriesContext(
            connection
        ) as ctx:
            operation.database_forwards(app_label, editor, project_state, new_state)
        Pony.objects.create(pink=1, weight=4.0)
        if connection.features.supports_deferrable_unique_constraints:
            # Unique constraint is deferred.
            with transaction.atomic():
                obj = Pony.objects.create(pink=1, weight=4.0)
                obj.pink = 2
                obj.save()
            # Constraint behavior can be changed with SET CONSTRAINTS.
            with self.assertRaises(IntegrityError):
                with transaction.atomic(), connection.cursor() as cursor:
                    quoted_name = connection.ops.quote_name(
                        deferred_unique_constraint.name
                    )
                    cursor.execute("SET CONSTRAINTS %s IMMEDIATE" % quoted_name)
                    obj = Pony.objects.create(pink=1, weight=4.0)
                    obj.pink = 3
                    obj.save()
        else:
            self.assertEqual(len(ctx), 0)
            Pony.objects.create(pink=1, weight=4.0)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        # Constraint doesn't work.
        Pony.objects.create(pink=1, weight=4.0)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"model_name": "Pony", "constraint": deferred_unique_constraint},
        )

    def test_remove_deferred_unique_constraint(self):
        app_label = "test_removedeferred_uc"
        deferred_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            name="deferred_pink_constraint_rm",
            deferrable=models.Deferrable.DEFERRED,
        )
        project_state = self.set_up_test_model(
            app_label, constraints=[deferred_unique_constraint]
        )
        operation = migrations.RemoveConstraint("Pony", deferred_unique_constraint.name)
        self.assertEqual(
            operation.describe(),
            "Remove constraint deferred_pink_constraint_rm from model Pony",
        )
        # Remove constraint.
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            len(new_state.models[app_label, "pony"].options["constraints"]), 0
        )
        Pony = new_state.apps.get_model(app_label, "Pony")
        self.assertEqual(len(Pony._meta.constraints), 0)
        with connection.schema_editor() as editor, CaptureQueriesContext(
            connection
        ) as ctx:
            operation.database_forwards(app_label, editor, project_state, new_state)
        # Constraint doesn't work.
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=4.0).delete()
        if not connection.features.supports_deferrable_unique_constraints:
            self.assertEqual(len(ctx), 0)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        if connection.features.supports_deferrable_unique_constraints:
            # Unique constraint is deferred.
            with transaction.atomic():
                obj = Pony.objects.create(pink=1, weight=4.0)
                obj.pink = 2
                obj.save()
            # Constraint behavior can be changed with SET CONSTRAINTS.
            with self.assertRaises(IntegrityError):
                with transaction.atomic(), connection.cursor() as cursor:
                    quoted_name = connection.ops.quote_name(
                        deferred_unique_constraint.name
                    )
                    cursor.execute("SET CONSTRAINTS %s IMMEDIATE" % quoted_name)
                    obj = Pony.objects.create(pink=1, weight=4.0)
                    obj.pink = 3
                    obj.save()
        else:
            Pony.objects.create(pink=1, weight=4.0)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "model_name": "Pony",
                "name": "deferred_pink_constraint_rm",
            },
        )

    def test_add_covering_unique_constraint(self):
        app_label = "test_addcovering_uc"
        project_state = self.set_up_test_model(app_label)
        covering_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            name="covering_pink_constraint_add",
            include=["weight"],
        )
        operation = migrations.AddConstraint("Pony", covering_unique_constraint)
        self.assertEqual(
            operation.describe(),
            "Create constraint covering_pink_constraint_add on model Pony",
        )
        # Add constraint.
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            len(new_state.models[app_label, "pony"].options["constraints"]), 1
        )
        Pony = new_state.apps.get_model(app_label, "Pony")
        self.assertEqual(len(Pony._meta.constraints), 1)
        with connection.schema_editor() as editor, CaptureQueriesContext(
            connection
        ) as ctx:
            operation.database_forwards(app_label, editor, project_state, new_state)
        Pony.objects.create(pink=1, weight=4.0)
        if connection.features.supports_covering_indexes:
            with self.assertRaises(IntegrityError):
                Pony.objects.create(pink=1, weight=4.0)
        else:
            self.assertEqual(len(ctx), 0)
            Pony.objects.create(pink=1, weight=4.0)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        # Constraint doesn't work.
        Pony.objects.create(pink=1, weight=4.0)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"model_name": "Pony", "constraint": covering_unique_constraint},
        )

    def test_remove_covering_unique_constraint(self):
        app_label = "test_removecovering_uc"
        covering_unique_constraint = models.UniqueConstraint(
            fields=["pink"],
            name="covering_pink_constraint_rm",
            include=["weight"],
        )
        project_state = self.set_up_test_model(
            app_label, constraints=[covering_unique_constraint]
        )
        operation = migrations.RemoveConstraint("Pony", covering_unique_constraint.name)
        self.assertEqual(
            operation.describe(),
            "Remove constraint covering_pink_constraint_rm from model Pony",
        )
        # Remove constraint.
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            len(new_state.models[app_label, "pony"].options["constraints"]), 0
        )
        Pony = new_state.apps.get_model(app_label, "Pony")
        self.assertEqual(len(Pony._meta.constraints), 0)
        with connection.schema_editor() as editor, CaptureQueriesContext(
            connection
        ) as ctx:
            operation.database_forwards(app_label, editor, project_state, new_state)
        # Constraint doesn't work.
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=4.0).delete()
        if not connection.features.supports_covering_indexes:
            self.assertEqual(len(ctx), 0)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        if connection.features.supports_covering_indexes:
            with self.assertRaises(IntegrityError):
                Pony.objects.create(pink=1, weight=4.0)
        else:
            Pony.objects.create(pink=1, weight=4.0)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {
                "model_name": "Pony",
                "name": "covering_pink_constraint_rm",
            },
        )

    def test_alter_field_with_func_unique_constraint(self):
        app_label = "test_alfuncuc"
        constraint_name = f"{app_label}_pony_uq"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(
            app_label,
            constraints=[
                models.UniqueConstraint("pink", "weight", name=constraint_name)
            ],
        )
        operation = migrations.AlterField(
            "Pony", "pink", models.IntegerField(null=True)
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        if connection.features.supports_expression_indexes:
            self.assertIndexNameExists(table_name, constraint_name)
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        if connection.features.supports_expression_indexes:
            self.assertIndexNameExists(table_name, constraint_name)

    def test_add_func_unique_constraint(self):
        app_label = "test_adfuncuc"
        constraint_name = f"{app_label}_pony_abs_uq"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(app_label)
        constraint = models.UniqueConstraint(Abs("weight"), name=constraint_name)
        operation = migrations.AddConstraint("Pony", constraint)
        self.assertEqual(
            operation.describe(),
            "Create constraint test_adfuncuc_pony_abs_uq on model Pony",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "pony_test_adfuncuc_pony_abs_uq",
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            len(new_state.models[app_label, "pony"].options["constraints"]), 1
        )
        self.assertIndexNameNotExists(table_name, constraint_name)
        # Add constraint.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        Pony = new_state.apps.get_model(app_label, "Pony")
        Pony.objects.create(weight=4.0)
        if connection.features.supports_expression_indexes:
            self.assertIndexNameExists(table_name, constraint_name)
            with self.assertRaises(IntegrityError):
                Pony.objects.create(weight=-4.0)
        else:
            self.assertIndexNameNotExists(table_name, constraint_name)
            Pony.objects.create(weight=-4.0)
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertIndexNameNotExists(table_name, constraint_name)
        # Constraint doesn't work.
        Pony.objects.create(weight=-4.0)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AddConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"model_name": "Pony", "constraint": constraint},
        )

    def test_remove_func_unique_constraint(self):
        app_label = "test_rmfuncuc"
        constraint_name = f"{app_label}_pony_abs_uq"
        table_name = f"{app_label}_pony"
        project_state = self.set_up_test_model(
            app_label,
            constraints=[
                models.UniqueConstraint(Abs("weight"), name=constraint_name),
            ],
        )
        self.assertTableExists(table_name)
        if connection.features.supports_expression_indexes:
            self.assertIndexNameExists(table_name, constraint_name)
        operation = migrations.RemoveConstraint("Pony", constraint_name)
        self.assertEqual(
            operation.describe(),
            "Remove constraint test_rmfuncuc_pony_abs_uq from model Pony",
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "remove_pony_test_rmfuncuc_pony_abs_uq",
        )
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        self.assertEqual(
            len(new_state.models[app_label, "pony"].options["constraints"]), 0
        )
        Pony = new_state.apps.get_model(app_label, "Pony")
        self.assertEqual(len(Pony._meta.constraints), 0)
        # Remove constraint.
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertIndexNameNotExists(table_name, constraint_name)
        # Constraint doesn't work.
        Pony.objects.create(pink=1, weight=4.0)
        Pony.objects.create(pink=1, weight=-4.0).delete()
        # Reversal.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        if connection.features.supports_expression_indexes:
            self.assertIndexNameExists(table_name, constraint_name)
            with self.assertRaises(IntegrityError):
                Pony.objects.create(weight=-4.0)
        else:
            self.assertIndexNameNotExists(table_name, constraint_name)
            Pony.objects.create(weight=-4.0)
        # Deconstruction.
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveConstraint")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Pony", "name": constraint_name})

    def test_alter_model_options(self):
        """
        Tests the AlterModelOptions operation.
        """
        project_state = self.set_up_test_model("test_almoop")
        # Test the state alteration (no DB alteration to test)
        operation = migrations.AlterModelOptions(
            "Pony", {"permissions": [("can_groom", "Can groom")]}
        )
        self.assertEqual(operation.describe(), "Change Meta options on Pony")
        self.assertEqual(operation.migration_name_fragment, "alter_pony_options")
        new_state = project_state.clone()
        operation.state_forwards("test_almoop", new_state)
        self.assertEqual(
            len(
                project_state.models["test_almoop", "pony"].options.get(
                    "permissions", []
                )
            ),
            0,
        )
        self.assertEqual(
            len(new_state.models["test_almoop", "pony"].options.get("permissions", [])),
            1,
        )
        self.assertEqual(
            new_state.models["test_almoop", "pony"].options["permissions"][0][0],
            "can_groom",
        )
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelOptions")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2],
            {"name": "Pony", "options": {"permissions": [("can_groom", "Can groom")]}},
        )

    def test_alter_model_options_emptying(self):
        """
        The AlterModelOptions operation removes keys from the dict (#23121)
        """
        project_state = self.set_up_test_model("test_almoop", options=True)
        # Test the state alteration (no DB alteration to test)
        operation = migrations.AlterModelOptions("Pony", {})
        self.assertEqual(operation.describe(), "Change Meta options on Pony")
        new_state = project_state.clone()
        operation.state_forwards("test_almoop", new_state)
        self.assertEqual(
            len(
                project_state.models["test_almoop", "pony"].options.get(
                    "permissions", []
                )
            ),
            1,
        )
        self.assertEqual(
            len(new_state.models["test_almoop", "pony"].options.get("permissions", [])),
            0,
        )
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelOptions")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"name": "Pony", "options": {}})

    def test_alter_order_with_respect_to(self):
        """
        Tests the AlterOrderWithRespectTo operation.
        """
        project_state = self.set_up_test_model("test_alorwrtto", related_model=True)
        # Test the state alteration
        operation = migrations.AlterOrderWithRespectTo("Rider", "pony")
        self.assertEqual(
            operation.describe(), "Set order_with_respect_to on Rider to pony"
        )
        self.assertEqual(
            operation.migration_name_fragment,
            "alter_rider_order_with_respect_to",
        )
        new_state = project_state.clone()
        operation.state_forwards("test_alorwrtto", new_state)
        self.assertIsNone(
            project_state.models["test_alorwrtto", "rider"].options.get(
                "order_with_respect_to", None
            )
        )
        self.assertEqual(
            new_state.models["test_alorwrtto", "rider"].options.get(
                "order_with_respect_to", None
            ),
            "pony",
        )
        # Make sure there's no matching index
        self.assertColumnNotExists("test_alorwrtto_rider", "_order")
        # Create some rows before alteration
        rendered_state = project_state.apps
        pony = rendered_state.get_model("test_alorwrtto", "Pony").objects.create(
            weight=50
        )
        rider1 = rendered_state.get_model("test_alorwrtto", "Rider").objects.create(
            pony=pony
        )
        rider1.friend = rider1
        rider1.save()
        rider2 = rendered_state.get_model("test_alorwrtto", "Rider").objects.create(
            pony=pony
        )
        rider2.friend = rider2
        rider2.save()
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_alorwrtto", editor, project_state, new_state
            )
        self.assertColumnExists("test_alorwrtto_rider", "_order")
        # Check for correct value in rows
        updated_riders = new_state.apps.get_model(
            "test_alorwrtto", "Rider"
        ).objects.all()
        self.assertEqual(updated_riders[0]._order, 0)
        self.assertEqual(updated_riders[1]._order, 0)
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_alorwrtto", editor, new_state, project_state
            )
        self.assertColumnNotExists("test_alorwrtto_rider", "_order")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterOrderWithRespectTo")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            definition[2], {"name": "Rider", "order_with_respect_to": "pony"}
        )

    def test_alter_model_managers(self):
        """
        The managers on a model are set.
        """
        project_state = self.set_up_test_model("test_almoma")
        # Test the state alteration
        operation = migrations.AlterModelManagers(
            "Pony",
            managers=[
                ("food_qs", FoodQuerySet.as_manager()),
                ("food_mgr", FoodManager("a", "b")),
                ("food_mgr_kwargs", FoodManager("x", "y", 3, 4)),
            ],
        )
        self.assertEqual(operation.describe(), "Change managers on Pony")
        self.assertEqual(operation.migration_name_fragment, "alter_pony_managers")
        managers = project_state.models["test_almoma", "pony"].managers
        self.assertEqual(managers, [])

        new_state = project_state.clone()
        operation.state_forwards("test_almoma", new_state)
        self.assertIn(("test_almoma", "pony"), new_state.models)
        managers = new_state.models["test_almoma", "pony"].managers
        self.assertEqual(managers[0][0], "food_qs")
        self.assertIsInstance(managers[0][1], models.Manager)
        self.assertEqual(managers[1][0], "food_mgr")
        self.assertIsInstance(managers[1][1], FoodManager)
        self.assertEqual(managers[1][1].args, ("a", "b", 1, 2))
        self.assertEqual(managers[2][0], "food_mgr_kwargs")
        self.assertIsInstance(managers[2][1], FoodManager)
        self.assertEqual(managers[2][1].args, ("x", "y", 3, 4))
        rendered_state = new_state.apps
        model = rendered_state.get_model("test_almoma", "pony")
        self.assertIsInstance(model.food_qs, models.Manager)
        self.assertIsInstance(model.food_mgr, FoodManager)
        self.assertIsInstance(model.food_mgr_kwargs, FoodManager)

    def test_alter_model_managers_emptying(self):
        """
        The managers on a model are set.
        """
        project_state = self.set_up_test_model("test_almomae", manager_model=True)
        # Test the state alteration
        operation = migrations.AlterModelManagers("Food", managers=[])
        self.assertEqual(operation.describe(), "Change managers on Food")
        self.assertIn(("test_almomae", "food"), project_state.models)
        managers = project_state.models["test_almomae", "food"].managers
        self.assertEqual(managers[0][0], "food_qs")
        self.assertIsInstance(managers[0][1], models.Manager)
        self.assertEqual(managers[1][0], "food_mgr")
        self.assertIsInstance(managers[1][1], FoodManager)
        self.assertEqual(managers[1][1].args, ("a", "b", 1, 2))
        self.assertEqual(managers[2][0], "food_mgr_kwargs")
        self.assertIsInstance(managers[2][1], FoodManager)
        self.assertEqual(managers[2][1].args, ("x", "y", 3, 4))

        new_state = project_state.clone()
        operation.state_forwards("test_almomae", new_state)
        managers = new_state.models["test_almomae", "food"].managers
        self.assertEqual(managers, [])

    def test_alter_fk(self):
        """
        Creating and then altering an FK works correctly
        and deals with the pending SQL (#23091)
        """
        project_state = self.set_up_test_model("test_alfk")
        # Test adding and then altering the FK in one go
        create_operation = migrations.CreateModel(
            name="Rider",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("pony", models.ForeignKey("Pony", models.CASCADE)),
            ],
        )
        create_state = project_state.clone()
        create_operation.state_forwards("test_alfk", create_state)
        alter_operation = migrations.AlterField(
            model_name="Rider",
            name="pony",
            field=models.ForeignKey("Pony", models.CASCADE, editable=False),
        )
        alter_state = create_state.clone()
        alter_operation.state_forwards("test_alfk", alter_state)
        with connection.schema_editor() as editor:
            create_operation.database_forwards(
                "test_alfk", editor, project_state, create_state
            )
            alter_operation.database_forwards(
                "test_alfk", editor, create_state, alter_state
            )

    def test_alter_fk_non_fk(self):
        """
        Altering an FK to a non-FK works (#23244)
        """
        # Test the state alteration
        operation = migrations.AlterField(
            model_name="Rider",
            name="pony",
            field=models.FloatField(),
        )
        project_state, new_state = self.make_test_state(
            "test_afknfk", operation, related_model=True
        )
        # Test the database alteration
        self.assertColumnExists("test_afknfk_rider", "pony_id")
        self.assertColumnNotExists("test_afknfk_rider", "pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_afknfk", editor, project_state, new_state)
        self.assertColumnExists("test_afknfk_rider", "pony")
        self.assertColumnNotExists("test_afknfk_rider", "pony_id")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_afknfk", editor, new_state, project_state
            )
        self.assertColumnExists("test_afknfk_rider", "pony_id")
        self.assertColumnNotExists("test_afknfk_rider", "pony")

    def test_run_sql(self):
        """
        Tests the RunSQL operation.
        """
        project_state = self.set_up_test_model("test_runsql")
        # Create the operation
        operation = migrations.RunSQL(
            # Use a multi-line string with a comment to test splitting on
            # SQLite and MySQL respectively.
            "CREATE TABLE i_love_ponies (id int, special_thing varchar(15));\n"
            "INSERT INTO i_love_ponies (id, special_thing) "
            "VALUES (1, 'i love ponies'); -- this is magic!\n"
            "INSERT INTO i_love_ponies (id, special_thing) "
            "VALUES (2, 'i love django');\n"
            "UPDATE i_love_ponies SET special_thing = 'Ponies' "
            "WHERE special_thing LIKE '%%ponies';"
            "UPDATE i_love_ponies SET special_thing = 'Django' "
            "WHERE special_thing LIKE '%django';",
            # Run delete queries to test for parameter substitution failure
            # reported in #23426
            "DELETE FROM i_love_ponies WHERE special_thing LIKE '%Django%';"
            "DELETE FROM i_love_ponies WHERE special_thing LIKE '%%Ponies%%';"
            "DROP TABLE i_love_ponies",
            state_operations=[
                migrations.CreateModel(
                    "SomethingElse", [("id", models.AutoField(primary_key=True))]
                )
            ],
        )
        self.assertEqual(operation.describe(), "Raw SQL operation")
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_runsql", new_state)
        self.assertEqual(
            len(new_state.models["test_runsql", "somethingelse"].fields), 1
        )
        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        # Test SQL collection
        with connection.schema_editor(collect_sql=True) as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)
            self.assertIn("LIKE '%%ponies';", "\n".join(editor.collected_sql))
            operation.database_backwards(
                "test_runsql", editor, project_state, new_state
            )
            self.assertIn("LIKE '%%Ponies%%';", "\n".join(editor.collected_sql))
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)
        self.assertTableExists("i_love_ponies")
        # Make sure all the SQL was processed
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 2)
            cursor.execute(
                "SELECT COUNT(*) FROM i_love_ponies WHERE special_thing = 'Django'"
            )
            self.assertEqual(cursor.fetchall()[0][0], 1)
            cursor.execute(
                "SELECT COUNT(*) FROM i_love_ponies WHERE special_thing = 'Ponies'"
            )
            self.assertEqual(cursor.fetchall()[0][0], 1)
        # And test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_runsql", editor, new_state, project_state
            )
        self.assertTableNotExists("i_love_ponies")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RunSQL")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            sorted(definition[2]), ["reverse_sql", "sql", "state_operations"]
        )
        # And elidable reduction
        self.assertIs(False, operation.reduce(operation, []))
        elidable_operation = migrations.RunSQL("SELECT 1 FROM void;", elidable=True)
        self.assertEqual(elidable_operation.reduce(operation, []), [operation])

    def test_run_sql_params(self):
        """
        #23426 - RunSQL should accept parameters.
        """
        project_state = self.set_up_test_model("test_runsql")
        # Create the operation
        operation = migrations.RunSQL(
            ["CREATE TABLE i_love_ponies (id int, special_thing varchar(15));"],
            ["DROP TABLE i_love_ponies"],
        )
        param_operation = migrations.RunSQL(
            # forwards
            (
                "INSERT INTO i_love_ponies (id, special_thing) VALUES (1, 'Django');",
                [
                    "INSERT INTO i_love_ponies (id, special_thing) VALUES (2, %s);",
                    ["Ponies"],
                ],
                (
                    "INSERT INTO i_love_ponies (id, special_thing) VALUES (%s, %s);",
                    (
                        3,
                        "Python",
                    ),
                ),
            ),
            # backwards
            [
                "DELETE FROM i_love_ponies WHERE special_thing = 'Django';",
                ["DELETE FROM i_love_ponies WHERE special_thing = 'Ponies';", None],
                (
                    "DELETE FROM i_love_ponies WHERE id = %s OR special_thing = %s;",
                    [3, "Python"],
                ),
            ],
        )

        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        new_state = project_state.clone()
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)

        # Test parameter passing
        with connection.schema_editor() as editor:
            param_operation.database_forwards(
                "test_runsql", editor, project_state, new_state
            )
        # Make sure all the SQL was processed
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 3)

        with connection.schema_editor() as editor:
            param_operation.database_backwards(
                "test_runsql", editor, new_state, project_state
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 0)

        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_runsql", editor, new_state, project_state
            )
        self.assertTableNotExists("i_love_ponies")

    def test_run_sql_params_invalid(self):
        """
        #23426 - RunSQL should fail when a list of statements with an incorrect
        number of tuples is given.
        """
        project_state = self.set_up_test_model("test_runsql")
        new_state = project_state.clone()
        operation = migrations.RunSQL(
            # forwards
            [["INSERT INTO foo (bar) VALUES ('buz');"]],
            # backwards
            (("DELETE FROM foo WHERE bar = 'buz';", "invalid", "parameter count"),),
        )

        with connection.schema_editor() as editor:
            with self.assertRaisesMessage(ValueError, "Expected a 2-tuple but got 1"):
                operation.database_forwards(
                    "test_runsql", editor, project_state, new_state
                )

        with connection.schema_editor() as editor:
            with self.assertRaisesMessage(ValueError, "Expected a 2-tuple but got 3"):
                operation.database_backwards(
                    "test_runsql", editor, new_state, project_state
                )

    def test_run_sql_noop(self):
        """
        #24098 - Tests no-op RunSQL operations.
        """
        operation = migrations.RunSQL(migrations.RunSQL.noop, migrations.RunSQL.noop)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, None, None)
            operation.database_backwards("test_runsql", editor, None, None)

    def test_run_sql_add_missing_semicolon_on_collect_sql(self):
        project_state = self.set_up_test_model("test_runsql")
        new_state = project_state.clone()
        tests = [
            "INSERT INTO test_runsql_pony (pink, weight) VALUES (1, 1);\n",
            "INSERT INTO test_runsql_pony (pink, weight) VALUES (1, 1)\n",
        ]
        for sql in tests:
            with self.subTest(sql=sql):
                operation = migrations.RunSQL(sql, migrations.RunPython.noop)
                with connection.schema_editor(collect_sql=True) as editor:
                    operation.database_forwards(
                        "test_runsql", editor, project_state, new_state
                    )
                    collected_sql = "\n".join(editor.collected_sql)
                    self.assertEqual(collected_sql.count(";"), 1)

    def test_run_python(self):
        """
        Tests the RunPython operation
        """

        project_state = self.set_up_test_model("test_runpython", mti_model=True)

        # Create the operation
        def inner_method(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            Pony.objects.create(pink=1, weight=3.55)
            Pony.objects.create(weight=5)

        def inner_method_reverse(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            Pony.objects.filter(pink=1, weight=3.55).delete()
            Pony.objects.filter(weight=5).delete()

        operation = migrations.RunPython(
            inner_method, reverse_code=inner_method_reverse
        )
        self.assertEqual(operation.describe(), "Raw Python operation")
        # Test the state alteration does nothing
        new_state = project_state.clone()
        operation.state_forwards("test_runpython", new_state)
        self.assertEqual(new_state, project_state)
        # Test the database alteration
        self.assertEqual(
            project_state.apps.get_model("test_runpython", "Pony").objects.count(), 0
        )
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_runpython", editor, project_state, new_state
            )
        self.assertEqual(
            project_state.apps.get_model("test_runpython", "Pony").objects.count(), 2
        )
        # Now test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_runpython", editor, project_state, new_state
            )
        self.assertEqual(
            project_state.apps.get_model("test_runpython", "Pony").objects.count(), 0
        )
        # Now test we can't use a string
        with self.assertRaisesMessage(
            ValueError, "RunPython must be supplied with a callable"
        ):
            migrations.RunPython("print 'ahahaha'")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RunPython")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["code", "reverse_code"])

        # Also test reversal fails, with an operation identical to above but
        # without reverse_code set.
        no_reverse_operation = migrations.RunPython(inner_method)
        self.assertFalse(no_reverse_operation.reversible)
        with connection.schema_editor() as editor:
            no_reverse_operation.database_forwards(
                "test_runpython", editor, project_state, new_state
            )
            with self.assertRaises(NotImplementedError):
                no_reverse_operation.database_backwards(
                    "test_runpython", editor, new_state, project_state
                )
        self.assertEqual(
            project_state.apps.get_model("test_runpython", "Pony").objects.count(), 2
        )

        def create_ponies(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            pony1 = Pony.objects.create(pink=1, weight=3.55)
            self.assertIsNot(pony1.pk, None)
            pony2 = Pony.objects.create(weight=5)
            self.assertIsNot(pony2.pk, None)
            self.assertNotEqual(pony1.pk, pony2.pk)

        operation = migrations.RunPython(create_ponies)
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_runpython", editor, project_state, new_state
            )
        self.assertEqual(
            project_state.apps.get_model("test_runpython", "Pony").objects.count(), 4
        )
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RunPython")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["code"])

        def create_shetlandponies(models, schema_editor):
            ShetlandPony = models.get_model("test_runpython", "ShetlandPony")
            pony1 = ShetlandPony.objects.create(weight=4.0)
            self.assertIsNot(pony1.pk, None)
            pony2 = ShetlandPony.objects.create(weight=5.0)
            self.assertIsNot(pony2.pk, None)
            self.assertNotEqual(pony1.pk, pony2.pk)

        operation = migrations.RunPython(create_shetlandponies)
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_runpython", editor, project_state, new_state
            )
        self.assertEqual(
            project_state.apps.get_model("test_runpython", "Pony").objects.count(), 6
        )
        self.assertEqual(
            project_state.apps.get_model(
                "test_runpython", "ShetlandPony"
            ).objects.count(),
            2,
        )
        # And elidable reduction
        self.assertIs(False, operation.reduce(operation, []))
        elidable_operation = migrations.RunPython(inner_method, elidable=True)
        self.assertEqual(elidable_operation.reduce(operation, []), [operation])

    def test_run_python_atomic(self):
        """
        Tests the RunPython operation correctly handles the "atomic" keyword
        """
        project_state = self.set_up_test_model("test_runpythonatomic", mti_model=True)

        def inner_method(models, schema_editor):
            Pony = models.get_model("test_runpythonatomic", "Pony")
            Pony.objects.create(pink=1, weight=3.55)
            raise ValueError("Adrian hates ponies.")

        # Verify atomicity when applying.
        atomic_migration = Migration("test", "test_runpythonatomic")
        atomic_migration.operations = [
            migrations.RunPython(inner_method, reverse_code=inner_method)
        ]
        non_atomic_migration = Migration("test", "test_runpythonatomic")
        non_atomic_migration.operations = [
            migrations.RunPython(inner_method, reverse_code=inner_method, atomic=False)
        ]
        # If we're a fully-transactional database, both versions should rollback
        if connection.features.can_rollback_ddl:
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.apply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.apply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
        # Otherwise, the non-atomic operation should leave a row there
        else:
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.apply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.apply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                1,
            )
        # Reset object count to zero and verify atomicity when unapplying.
        project_state.apps.get_model(
            "test_runpythonatomic", "Pony"
        ).objects.all().delete()
        # On a fully-transactional database, both versions rollback.
        if connection.features.can_rollback_ddl:
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.unapply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.unapply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
        # Otherwise, the non-atomic operation leaves a row there.
        else:
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.unapply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                0,
            )
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.unapply(project_state, editor)
            self.assertEqual(
                project_state.apps.get_model(
                    "test_runpythonatomic", "Pony"
                ).objects.count(),
                1,
            )
        # Verify deconstruction.
        definition = non_atomic_migration.operations[0].deconstruct()
        self.assertEqual(definition[0], "RunPython")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["atomic", "code", "reverse_code"])

    def test_run_python_related_assignment(self):
        """
        #24282 - Model changes to a FK reverse side update the model
        on the FK side as well.
        """

        def inner_method(models, schema_editor):
            Author = models.get_model("test_authors", "Author")
            Book = models.get_model("test_books", "Book")
            author = Author.objects.create(name="Hemingway")
            Book.objects.create(title="Old Man and The Sea", author=author)

        create_author = migrations.CreateModel(
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={},
        )
        create_book = migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("title", models.CharField(max_length=100)),
                ("author", models.ForeignKey("test_authors.Author", models.CASCADE)),
            ],
            options={},
        )
        add_hometown = migrations.AddField(
            "Author",
            "hometown",
            models.CharField(max_length=100),
        )
        create_old_man = migrations.RunPython(inner_method, inner_method)

        project_state = ProjectState()
        new_state = project_state.clone()
        with connection.schema_editor() as editor:
            create_author.state_forwards("test_authors", new_state)
            create_author.database_forwards(
                "test_authors", editor, project_state, new_state
            )
        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_book.state_forwards("test_books", new_state)
            create_book.database_forwards(
                "test_books", editor, project_state, new_state
            )
        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            add_hometown.state_forwards("test_authors", new_state)
            add_hometown.database_forwards(
                "test_authors", editor, project_state, new_state
            )
        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_old_man.state_forwards("test_books", new_state)
            create_old_man.database_forwards(
                "test_books", editor, project_state, new_state
            )

    def test_model_with_bigautofield(self):
        """
        A model with BigAutoField can be created.
        """

        def create_data(models, schema_editor):
            Author = models.get_model("test_author", "Author")
            Book = models.get_model("test_book", "Book")
            author1 = Author.objects.create(name="Hemingway")
            Book.objects.create(title="Old Man and The Sea", author=author1)
            Book.objects.create(id=2**33, title="A farewell to arms", author=author1)

            author2 = Author.objects.create(id=2**33, name="Remarque")
            Book.objects.create(title="All quiet on the western front", author=author2)
            Book.objects.create(title="Arc de Triomphe", author=author2)

        create_author = migrations.CreateModel(
            "Author",
            [
                ("id", models.BigAutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={},
        )
        create_book = migrations.CreateModel(
            "Book",
            [
                ("id", models.BigAutoField(primary_key=True)),
                ("title", models.CharField(max_length=100)),
                (
                    "author",
                    models.ForeignKey(
                        to="test_author.Author", on_delete=models.CASCADE
                    ),
                ),
            ],
            options={},
        )
        fill_data = migrations.RunPython(create_data)

        project_state = ProjectState()
        new_state = project_state.clone()
        with connection.schema_editor() as editor:
            create_author.state_forwards("test_author", new_state)
            create_author.database_forwards(
                "test_author", editor, project_state, new_state
            )

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_book.state_forwards("test_book", new_state)
            create_book.database_forwards("test_book", editor, project_state, new_state)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            fill_data.state_forwards("fill_data", new_state)
            fill_data.database_forwards("fill_data", editor, project_state, new_state)

    def _test_autofield_foreignfield_growth(
        self, source_field, target_field, target_value
    ):
        """
        A field may be migrated in the following ways:

        - AutoField to BigAutoField
        - SmallAutoField to AutoField
        - SmallAutoField to BigAutoField
        """

        def create_initial_data(models, schema_editor):
            Article = models.get_model("test_article", "Article")
            Blog = models.get_model("test_blog", "Blog")
            blog = Blog.objects.create(name="web development done right")
            Article.objects.create(name="Frameworks", blog=blog)
            Article.objects.create(name="Programming Languages", blog=blog)

        def create_big_data(models, schema_editor):
            Article = models.get_model("test_article", "Article")
            Blog = models.get_model("test_blog", "Blog")
            blog2 = Blog.objects.create(name="Frameworks", id=target_value)
            Article.objects.create(name="Django", blog=blog2)
            Article.objects.create(id=target_value, name="Django2", blog=blog2)

        create_blog = migrations.CreateModel(
            "Blog",
            [
                ("id", source_field(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={},
        )
        create_article = migrations.CreateModel(
            "Article",
            [
                ("id", source_field(primary_key=True)),
                (
                    "blog",
                    models.ForeignKey(to="test_blog.Blog", on_delete=models.CASCADE),
                ),
                ("name", models.CharField(max_length=100)),
                ("data", models.TextField(default="")),
            ],
            options={},
        )
        fill_initial_data = migrations.RunPython(
            create_initial_data, create_initial_data
        )
        fill_big_data = migrations.RunPython(create_big_data, create_big_data)

        grow_article_id = migrations.AlterField(
            "Article", "id", target_field(primary_key=True)
        )
        grow_blog_id = migrations.AlterField(
            "Blog", "id", target_field(primary_key=True)
        )

        project_state = ProjectState()
        new_state = project_state.clone()
        with connection.schema_editor() as editor:
            create_blog.state_forwards("test_blog", new_state)
            create_blog.database_forwards("test_blog", editor, project_state, new_state)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_article.state_forwards("test_article", new_state)
            create_article.database_forwards(
                "test_article", editor, project_state, new_state
            )

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            fill_initial_data.state_forwards("fill_initial_data", new_state)
            fill_initial_data.database_forwards(
                "fill_initial_data", editor, project_state, new_state
            )

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            grow_article_id.state_forwards("test_article", new_state)
            grow_article_id.database_forwards(
                "test_article", editor, project_state, new_state
            )

        state = new_state.clone()
        article = state.apps.get_model("test_article.Article")
        self.assertIsInstance(article._meta.pk, target_field)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            grow_blog_id.state_forwards("test_blog", new_state)
            grow_blog_id.database_forwards(
                "test_blog", editor, project_state, new_state
            )

        state = new_state.clone()
        blog = state.apps.get_model("test_blog.Blog")
        self.assertIsInstance(blog._meta.pk, target_field)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            fill_big_data.state_forwards("fill_big_data", new_state)
            fill_big_data.database_forwards(
                "fill_big_data", editor, project_state, new_state
            )

    def test_autofield__bigautofield_foreignfield_growth(self):
        """A field may be migrated from AutoField to BigAutoField."""
        self._test_autofield_foreignfield_growth(
            models.AutoField,
            models.BigAutoField,
            2**33,
        )

    def test_smallfield_autofield_foreignfield_growth(self):
        """A field may be migrated from SmallAutoField to AutoField."""
        self._test_autofield_foreignfield_growth(
            models.SmallAutoField,
            models.AutoField,
            2**22,
        )

    def test_smallfield_bigautofield_foreignfield_growth(self):
        """A field may be migrated from SmallAutoField to BigAutoField."""
        self._test_autofield_foreignfield_growth(
            models.SmallAutoField,
            models.BigAutoField,
            2**33,
        )

    def test_run_python_noop(self):
        """
        #24098 - Tests no-op RunPython operations.
        """
        project_state = ProjectState()
        new_state = project_state.clone()
        operation = migrations.RunPython(
            migrations.RunPython.noop, migrations.RunPython.noop
        )
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_runpython", editor, project_state, new_state
            )
            operation.database_backwards(
                "test_runpython", editor, new_state, project_state
            )

    def test_separate_database_and_state(self):
        """
        Tests the SeparateDatabaseAndState operation.
        """
        project_state = self.set_up_test_model("test_separatedatabaseandstate")
        # Create the operation
        database_operation = migrations.RunSQL(
            "CREATE TABLE i_love_ponies (id int, special_thing int);",
            "DROP TABLE i_love_ponies;",
        )
        state_operation = migrations.CreateModel(
            "SomethingElse", [("id", models.AutoField(primary_key=True))]
        )
        operation = migrations.SeparateDatabaseAndState(
            state_operations=[state_operation], database_operations=[database_operation]
        )
        self.assertEqual(
            operation.describe(), "Custom state/database change combination"
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_separatedatabaseandstate", new_state)
        self.assertEqual(
            len(
                new_state.models[
                    "test_separatedatabaseandstate", "somethingelse"
                ].fields
            ),
            1,
        )
        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_separatedatabaseandstate", editor, project_state, new_state
            )
        self.assertTableExists("i_love_ponies")
        # And test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_separatedatabaseandstate", editor, new_state, project_state
            )
        self.assertTableNotExists("i_love_ponies")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "SeparateDatabaseAndState")
        self.assertEqual(definition[1], [])
        self.assertEqual(
            sorted(definition[2]), ["database_operations", "state_operations"]
        )

    def test_separate_database_and_state2(self):
        """
        A complex SeparateDatabaseAndState operation: Multiple operations both
        for state and database. Verify the state dependencies within each list
        and that state ops don't affect the database.
        """
        app_label = "test_separatedatabaseandstate2"
        project_state = self.set_up_test_model(app_label)
        # Create the operation
        database_operations = [
            migrations.CreateModel(
                "ILovePonies",
                [("id", models.AutoField(primary_key=True))],
                options={"db_table": "iloveponies"},
            ),
            migrations.CreateModel(
                "ILoveMorePonies",
                # We use IntegerField and not AutoField because
                # the model is going to be deleted immediately
                # and with an AutoField this fails on Oracle
                [("id", models.IntegerField(primary_key=True))],
                options={"db_table": "ilovemoreponies"},
            ),
            migrations.DeleteModel("ILoveMorePonies"),
            migrations.CreateModel(
                "ILoveEvenMorePonies",
                [("id", models.AutoField(primary_key=True))],
                options={"db_table": "iloveevenmoreponies"},
            ),
        ]
        state_operations = [
            migrations.CreateModel(
                "SomethingElse",
                [("id", models.AutoField(primary_key=True))],
                options={"db_table": "somethingelse"},
            ),
            migrations.DeleteModel("SomethingElse"),
            migrations.CreateModel(
                "SomethingCompletelyDifferent",
                [("id", models.AutoField(primary_key=True))],
                options={"db_table": "somethingcompletelydifferent"},
            ),
        ]
        operation = migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=database_operations,
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)

        def assertModelsAndTables(after_db):
            # Tables and models exist, or don't, as they should:
            self.assertNotIn((app_label, "somethingelse"), new_state.models)
            self.assertEqual(
                len(new_state.models[app_label, "somethingcompletelydifferent"].fields),
                1,
            )
            self.assertNotIn((app_label, "iloveponiesonies"), new_state.models)
            self.assertNotIn((app_label, "ilovemoreponies"), new_state.models)
            self.assertNotIn((app_label, "iloveevenmoreponies"), new_state.models)
            self.assertTableNotExists("somethingelse")
            self.assertTableNotExists("somethingcompletelydifferent")
            self.assertTableNotExists("ilovemoreponies")
            if after_db:
                self.assertTableExists("iloveponies")
                self.assertTableExists("iloveevenmoreponies")
            else:
                self.assertTableNotExists("iloveponies")
                self.assertTableNotExists("iloveevenmoreponies")

        assertModelsAndTables(after_db=False)
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)
        assertModelsAndTables(after_db=True)
        # And test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)
        assertModelsAndTables(after_db=False)


class SwappableOperationTests(OperationTestBase):
    """
    Key operations ignore swappable models
    (we don't want to replicate all of them here, as the functionality
    is in a common base class anyway)
    """

    available_apps = ["migrations"]

    @override_settings(TEST_SWAP_MODEL="migrations.SomeFakeModel")
    def test_create_ignore_swapped(self):
        """
        The CreateTable operation ignores swapped models.
        """
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
            options={
                "swappable": "TEST_SWAP_MODEL",
            },
        )
        # Test the state alteration (it should still be there!)
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crigsw", new_state)
        self.assertEqual(new_state.models["test_crigsw", "pony"].name, "Pony")
        self.assertEqual(len(new_state.models["test_crigsw", "pony"].fields), 2)
        # Test the database alteration
        self.assertTableNotExists("test_crigsw_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crigsw", editor, project_state, new_state)
        self.assertTableNotExists("test_crigsw_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_crigsw", editor, new_state, project_state
            )
        self.assertTableNotExists("test_crigsw_pony")

    @override_settings(TEST_SWAP_MODEL="migrations.SomeFakeModel")
    def test_delete_ignore_swapped(self):
        """
        Tests the DeleteModel operation ignores swapped models.
        """
        operation = migrations.DeleteModel("Pony")
        project_state, new_state = self.make_test_state("test_dligsw", operation)
        # Test the database alteration
        self.assertTableNotExists("test_dligsw_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_dligsw", editor, project_state, new_state)
        self.assertTableNotExists("test_dligsw_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_dligsw", editor, new_state, project_state
            )
        self.assertTableNotExists("test_dligsw_pony")

    @override_settings(TEST_SWAP_MODEL="migrations.SomeFakeModel")
    def test_add_field_ignore_swapped(self):
        """
        Tests the AddField operation.
        """
        # Test the state alteration
        operation = migrations.AddField(
            "Pony",
            "height",
            models.FloatField(null=True, default=5),
        )
        project_state, new_state = self.make_test_state("test_adfligsw", operation)
        # Test the database alteration
        self.assertTableNotExists("test_adfligsw_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_adfligsw", editor, project_state, new_state
            )
        self.assertTableNotExists("test_adfligsw_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(
                "test_adfligsw", editor, new_state, project_state
            )
        self.assertTableNotExists("test_adfligsw_pony")

    @override_settings(TEST_SWAP_MODEL="migrations.SomeFakeModel")
    def test_indexes_ignore_swapped(self):
        """
        Add/RemoveIndex operations ignore swapped models.
        """
        operation = migrations.AddIndex(
            "Pony", models.Index(fields=["pink"], name="my_name_idx")
        )
        project_state, new_state = self.make_test_state("test_adinigsw", operation)
        with connection.schema_editor() as editor:
            # No database queries should be run for swapped models
            operation.database_forwards(
                "test_adinigsw", editor, project_state, new_state
            )
            operation.database_backwards(
                "test_adinigsw", editor, new_state, project_state
            )

        operation = migrations.RemoveIndex(
            "Pony", models.Index(fields=["pink"], name="my_name_idx")
        )
        project_state, new_state = self.make_test_state("test_rminigsw", operation)
        with connection.schema_editor() as editor:
            operation.database_forwards(
                "test_rminigsw", editor, project_state, new_state
            )
            operation.database_backwards(
                "test_rminigsw", editor, new_state, project_state
            )


class TestCreateModel(SimpleTestCase):
    def test_references_model_mixin(self):
        migrations.CreateModel(
            "name",
            fields=[],
            bases=(Mixin, models.Model),
        ).references_model("other_model", "migrations")


class FieldOperationTests(SimpleTestCase):
    def test_references_model(self):
        operation = FieldOperation(
            "MoDel", "field", models.ForeignKey("Other", models.CASCADE)
        )
        # Model name match.
        self.assertIs(operation.references_model("mOdEl", "migrations"), True)
        # Referenced field.
        self.assertIs(operation.references_model("oTher", "migrations"), True)
        # Doesn't reference.
        self.assertIs(operation.references_model("Whatever", "migrations"), False)

    def test_references_field_by_name(self):
        operation = FieldOperation("MoDel", "field", models.BooleanField(default=False))
        self.assertIs(operation.references_field("model", "field", "migrations"), True)

    def test_references_field_by_remote_field_model(self):
        operation = FieldOperation(
            "Model", "field", models.ForeignKey("Other", models.CASCADE)
        )
        self.assertIs(
            operation.references_field("Other", "whatever", "migrations"), True
        )
        self.assertIs(
            operation.references_field("Missing", "whatever", "migrations"), False
        )

    def test_references_field_by_from_fields(self):
        operation = FieldOperation(
            "Model",
            "field",
            models.fields.related.ForeignObject(
                "Other", models.CASCADE, ["from"], ["to"]
            ),
        )
        self.assertIs(operation.references_field("Model", "from", "migrations"), True)
        self.assertIs(operation.references_field("Model", "to", "migrations"), False)
        self.assertIs(operation.references_field("Other", "from", "migrations"), False)
        self.assertIs(operation.references_field("Model", "to", "migrations"), False)

    def test_references_field_by_to_fields(self):
        operation = FieldOperation(
            "Model",
            "field",
            models.ForeignKey("Other", models.CASCADE, to_field="field"),
        )
        self.assertIs(operation.references_field("Other", "field", "migrations"), True)
        self.assertIs(
            operation.references_field("Other", "whatever", "migrations"), False
        )
        self.assertIs(
            operation.references_field("Missing", "whatever", "migrations"), False
        )

    def test_references_field_by_through(self):
        operation = FieldOperation(
            "Model", "field", models.ManyToManyField("Other", through="Through")
        )
        self.assertIs(
            operation.references_field("Other", "whatever", "migrations"), True
        )
        self.assertIs(
            operation.references_field("Through", "whatever", "migrations"), True
        )
        self.assertIs(
            operation.references_field("Missing", "whatever", "migrations"), False
        )

    def test_reference_field_by_through_fields(self):
        operation = FieldOperation(
            "Model",
            "field",
            models.ManyToManyField(
                "Other", through="Through", through_fields=("first", "second")
            ),
        )
        self.assertIs(
            operation.references_field("Other", "whatever", "migrations"), True
        )
        self.assertIs(
            operation.references_field("Through", "whatever", "migrations"), False
        )
        self.assertIs(
            operation.references_field("Through", "first", "migrations"), True
        )
        self.assertIs(
            operation.references_field("Through", "second", "migrations"), True
        )
