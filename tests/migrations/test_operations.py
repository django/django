from django.test import TestCase
from django.db import connection, models, migrations
from django.db.transaction import atomic
from django.db.utils import IntegrityError
from django.db.migrations.state import ProjectState


class OperationTests(TestCase):
    """
    Tests running the operations and making sure they do what they say they do.
    Each test looks at their state changing, and then their database operation -
    both forwards and backwards.
    """

    def assertTableExists(self, table):
        self.assertIn(table, connection.introspection.get_table_list(connection.cursor()))

    def assertTableNotExists(self, table):
        self.assertNotIn(table, connection.introspection.get_table_list(connection.cursor()))

    def assertColumnExists(self, table, column):
        self.assertIn(column, [c.name for c in connection.introspection.get_table_description(connection.cursor(), table)])

    def assertColumnNotExists(self, table, column):
        self.assertNotIn(column, [c.name for c in connection.introspection.get_table_description(connection.cursor(), table)])

    def assertColumnNull(self, table, column):
        self.assertEqual([c.null_ok for c in connection.introspection.get_table_description(connection.cursor(), table) if c.name == column][0], True)

    def assertColumnNotNull(self, table, column):
        self.assertEqual([c.null_ok for c in connection.introspection.get_table_description(connection.cursor(), table) if c.name == column][0], False)

    def set_up_test_model(self, app_label):
        """
        Creates a test model state and database table.
        """
        # Make the "current" state
        creation = migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
        )
        project_state = ProjectState()
        creation.state_forwards(app_label, project_state)
        # Set up the database
        with connection.schema_editor() as editor:
            creation.database_forwards(app_label, editor, ProjectState(), project_state)
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
        self.assertEqual(new_state.models["test_crmo", "pony"].name, "pony")
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
