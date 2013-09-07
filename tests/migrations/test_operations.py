from django.db import connection, models, migrations, router
from django.db.transaction import atomic
from django.db.utils import IntegrityError
from django.db.migrations.state import ProjectState
from .test_base import MigrationTestBase


class OperationTests(MigrationTestBase):
    """
    Tests running the operations and making sure they do what they say they do.
    Each test looks at their state changing, and then their database operation -
    both forwards and backwards.
    """

    def set_up_test_model(self, app_label, second_model=False):
        """
        Creates a test model state and database table.
        """
        # Make the "current" state
        operations = [migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
        )]
        if second_model:
            operations.append(migrations.CreateModel("Stable", [("id", models.AutoField(primary_key=True))]))
        project_state = ProjectState()
        for operation in operations:
            operation.state_forwards(app_label, project_state)
        # Set up the database
        with connection.schema_editor() as editor:
            for operation in operations:
                operation.database_forwards(app_label, editor, ProjectState(), project_state)
        return project_state

    def test_create_model(self):
        """
        Tests the CreateModel operation.
        Most other tests use this operation as part of setup, so check failures here first.
        """
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
        )
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
        self.assertEqual(len(definition[1]), 2)
        self.assertEqual(len(definition[2]), 0)
        self.assertEqual(definition[1][0], "Pony")

    def test_delete_model(self):
        """
        Tests the DeleteModel operation.
        """
        project_state = self.set_up_test_model("test_dlmo")
        # Test the state alteration
        operation = migrations.DeleteModel("Pony")
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

    def test_add_field(self):
        """
        Tests the AddField operation.
        """
        project_state = self.set_up_test_model("test_adfl")
        # Test the state alteration
        operation = migrations.AddField("Pony", "height", models.FloatField(null=True))
        new_state = project_state.clone()
        operation.state_forwards("test_adfl", new_state)
        self.assertEqual(len(new_state.models["test_adfl", "pony"].fields), 4)
        # Test the database alteration
        self.assertColumnNotExists("test_adfl_pony", "height")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adfl", editor, project_state, new_state)
        self.assertColumnExists("test_adfl_pony", "height")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adfl", editor, new_state, project_state)
        self.assertColumnNotExists("test_adfl_pony", "height")

    def test_add_field_m2m(self):
        """
        Tests the AddField operation with a ManyToManyField.
        """
        project_state = self.set_up_test_model("test_adflmm", second_model=True)
        # Test the state alteration
        operation = migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies"))
        new_state = project_state.clone()
        operation.state_forwards("test_adflmm", new_state)
        self.assertEqual(len(new_state.models["test_adflmm", "pony"].fields), 4)
        # Test the database alteration
        self.assertTableNotExists("test_adflmm_pony_stables")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_adflmm", editor, project_state, new_state)
        self.assertTableExists("test_adflmm_pony_stables")
        self.assertColumnNotExists("test_adflmm_pony", "stables")
        # Make sure the M2M field actually works
        with atomic():
            app_cache = new_state.render()
            Pony = app_cache.get_model("test_adflmm", "Pony")
            p = Pony.objects.create(pink=False, weight=4.55)
            p.stables.create()
            self.assertEqual(p.stables.count(), 1)
            p.stables.all().delete()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adflmm", editor, new_state, project_state)
        self.assertTableNotExists("test_adflmm_pony_stables")

    def test_remove_field(self):
        """
        Tests the RemoveField operation.
        """
        project_state = self.set_up_test_model("test_rmfl")
        # Test the state alteration
        operation = migrations.RemoveField("Pony", "pink")
        new_state = project_state.clone()
        operation.state_forwards("test_rmfl", new_state)
        self.assertEqual(len(new_state.models["test_rmfl", "pony"].fields), 2)
        # Test the database alteration
        self.assertColumnExists("test_rmfl_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rmfl", editor, project_state, new_state)
        self.assertColumnNotExists("test_rmfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rmfl", editor, new_state, project_state)
        self.assertColumnExists("test_rmfl_pony", "pink")

    def test_alter_model_table(self):
        """
        Tests the AlterModelTable operation.
        """
        project_state = self.set_up_test_model("test_almota")
        # Test the state alteration
        operation = migrations.AlterModelTable("Pony", "test_almota_pony_2")
        new_state = project_state.clone()
        operation.state_forwards("test_almota", new_state)
        self.assertEqual(new_state.models["test_almota", "pony"].options["db_table"], "test_almota_pony_2")
        # Test the database alteration
        self.assertTableExists("test_almota_pony")
        self.assertTableNotExists("test_almota_pony_2")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_almota", editor, project_state, new_state)
        self.assertTableNotExists("test_almota_pony")
        self.assertTableExists("test_almota_pony_2")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_almota", editor, new_state, project_state)
        self.assertTableExists("test_almota_pony")
        self.assertTableNotExists("test_almota_pony_2")

    def test_alter_field(self):
        """
        Tests the AlterField operation.
        """
        project_state = self.set_up_test_model("test_alfl")
        # Test the state alteration
        operation = migrations.AlterField("Pony", "pink", models.IntegerField(null=True))
        new_state = project_state.clone()
        operation.state_forwards("test_alfl", new_state)
        self.assertEqual(project_state.models["test_alfl", "pony"].get_field_by_name("pink").null, False)
        self.assertEqual(new_state.models["test_alfl", "pony"].get_field_by_name("pink").null, True)
        # Test the database alteration
        self.assertColumnNotNull("test_alfl_pony", "pink")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alfl", editor, project_state, new_state)
        self.assertColumnNull("test_alfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alfl", editor, new_state, project_state)
        self.assertColumnNotNull("test_alfl_pony", "pink")

    def test_rename_field(self):
        """
        Tests the RenameField operation.
        """
        project_state = self.set_up_test_model("test_rnfl")
        # Test the state alteration
        operation = migrations.RenameField("Pony", "pink", "blue")
        new_state = project_state.clone()
        operation.state_forwards("test_rnfl", new_state)
        self.assertIn("blue", [n for n, f in new_state.models["test_rnfl", "pony"].fields])
        self.assertNotIn("pink", [n for n, f in new_state.models["test_rnfl", "pony"].fields])
        # Test the database alteration
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnfl", editor, project_state, new_state)
        self.assertColumnExists("test_rnfl_pony", "blue")
        self.assertColumnNotExists("test_rnfl_pony", "pink")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rnfl", editor, new_state, project_state)
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")

    def test_alter_unique_together(self):
        """
        Tests the AlterUniqueTogether operation.
        """
        project_state = self.set_up_test_model("test_alunto")
        # Test the state alteration
        operation = migrations.AlterUniqueTogether("Pony", [("pink", "weight")])
        new_state = project_state.clone()
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(len(project_state.models["test_alunto", "pony"].options.get("unique_together", set())), 0)
        self.assertEqual(len(new_state.models["test_alunto", "pony"].options.get("unique_together", set())), 1)
        # Make sure we can insert duplicate rows
        cursor = connection.cursor()
        cursor.execute("INSERT INTO test_alunto_pony (id, pink, weight) VALUES (1, 1, 1)")
        cursor.execute("INSERT INTO test_alunto_pony (id, pink, weight) VALUES (2, 1, 1)")
        cursor.execute("DELETE FROM test_alunto_pony")
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alunto", editor, project_state, new_state)
        cursor.execute("INSERT INTO test_alunto_pony (id, pink, weight) VALUES (1, 1, 1)")
        with self.assertRaises(IntegrityError):
            with atomic():
                cursor.execute("INSERT INTO test_alunto_pony (id, pink, weight) VALUES (2, 1, 1)")
        cursor.execute("DELETE FROM test_alunto_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alunto", editor, new_state, project_state)
        cursor.execute("INSERT INTO test_alunto_pony (id, pink, weight) VALUES (1, 1, 1)")
        cursor.execute("INSERT INTO test_alunto_pony (id, pink, weight) VALUES (2, 1, 1)")
        cursor.execute("DELETE FROM test_alunto_pony")

    def test_alter_index_together(self):
        """
        Tests the AlterIndexTogether operation.
        """
        project_state = self.set_up_test_model("test_alinto")
        # Test the state alteration
        operation = migrations.AlterIndexTogether("Pony", [("pink", "weight")])
        new_state = project_state.clone()
        operation.state_forwards("test_alinto", new_state)
        self.assertEqual(len(project_state.models["test_alinto", "pony"].options.get("index_together", set())), 0)
        self.assertEqual(len(new_state.models["test_alinto", "pony"].options.get("index_together", set())), 1)
        # Make sure there's no matching index
        self.assertIndexNotExists("test_alinto_pony", ["pink", "weight"])
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alinto", editor, project_state, new_state)
        self.assertIndexExists("test_alinto_pony", ["pink", "weight"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alinto", editor, new_state, project_state)
        self.assertIndexNotExists("test_alinto_pony", ["pink", "weight"])

    def test_run_sql(self):
        """
        Tests the AlterIndexTogether operation.
        """
        project_state = self.set_up_test_model("test_runsql")
        # Create the operation
        operation = migrations.RunSQL(
            "CREATE TABLE i_love_ponies (id int, special_thing int)",
            "DROP TABLE i_love_ponies",
            state_operations = [migrations.CreateModel("SomethingElse", [("id", models.AutoField(primary_key=True))])],
        )
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_runsql", new_state)
        self.assertEqual(len(new_state.models["test_runsql", "somethingelse"].fields), 1)
        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)
        self.assertTableExists("i_love_ponies")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_runsql", editor, new_state, project_state)
        self.assertTableNotExists("i_love_ponies")


class MigrateNothingRouter(object):
    """
    A router that sends all writes to the other database.
    """
    def allow_migrate(self, db, model):
        return False


class MultiDBOperationTests(MigrationTestBase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [MigrateNothingRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_create_model(self):
        """
        Tests that CreateModel honours multi-db settings.
        """
        operation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=1)),
            ],
        )
        # Test the state alteration
        project_state = ProjectState()
        new_state = project_state.clone()
        operation.state_forwards("test_crmo", new_state)
        # Test the database alteration
        self.assertTableNotExists("test_crmo_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_crmo", editor, project_state, new_state)
        self.assertTableNotExists("test_crmo_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_crmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crmo_pony")
