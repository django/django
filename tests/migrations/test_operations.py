import unittest

from django.db import connection, migrations, models, transaction
from django.db.migrations.migration import Migration
from django.db.migrations.operations import CreateModel
from django.db.migrations.state import ModelState, ProjectState
from django.db.models.fields import NOT_PROVIDED
from django.db.transaction import atomic
from django.db.utils import IntegrityError
from django.test import SimpleTestCase, override_settings, skipUnlessDBFeature

from .models import FoodManager, FoodQuerySet, UnicodeModel
from .test_base import MigrationTestBase

try:
    import sqlparse
except ImportError:
    sqlparse = None


class Mixin(object):
    pass


class OperationTestBase(MigrationTestBase):
    """
    Common functions to help test operations.
    """

    def apply_operations(self, app_label, project_state, operations):
        migration = Migration('name', app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.apply(project_state, editor)

    def unapply_operations(self, app_label, project_state, operations):
        migration = Migration('name', app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.unapply(project_state, editor)

    def make_test_state(self, app_label, operation, **kwargs):
        """
        Makes a test state using set_up_test_model and returns the
        original state and the state after the migration is applied.
        """
        project_state = self.set_up_test_model(app_label, **kwargs)
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        return project_state, new_state

    def set_up_test_model(
            self, app_label, second_model=False, third_model=False, index=False, multicol_index=False,
            related_model=False, mti_model=False, proxy_model=False, manager_model=False,
            unique_together=False, options=False, db_table=None, index_together=False):
        """
        Creates a test model state and database table.
        """
        # Delete the tables if they already exist
        table_names = [
            # Start with ManyToMany tables
            '_pony_stables', '_pony_vans',
            # Then standard model tables
            '_pony', '_stable', '_van',
        ]
        tables = [(app_label + table_name) for table_name in table_names]
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            connection.disable_constraint_checking()
            sql_delete_table = connection.schema_editor().sql_delete_table
            with transaction.atomic():
                for table in tables:
                    if table in table_names:
                        cursor.execute(sql_delete_table % {
                            "table": connection.ops.quote_name(table),
                        })
            connection.enable_constraint_checking()

        # Make the "current" state
        model_options = {
            "swappable": "TEST_SWAP_MODEL",
            "index_together": [["weight", "pink"]] if index_together else [],
            "unique_together": [["pink", "weight"]] if unique_together else [],
        }
        if options:
            model_options["permissions"] = [("can_groom", "Can groom")]
        if db_table:
            model_options["db_table"] = db_table
        operations = [migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
            options=model_options,
        )]
        if index:
            operations.append(migrations.AddIndex(
                "Pony",
                models.Index(fields=["pink"], name="pony_pink_idx")
            ))
        if multicol_index:
            operations.append(migrations.AddIndex(
                "Pony",
                models.Index(fields=["pink", "weight"], name="pony_test_idx")
            ))
        if second_model:
            operations.append(migrations.CreateModel(
                "Stable",
                [
                    ("id", models.AutoField(primary_key=True)),
                ]
            ))
        if third_model:
            operations.append(migrations.CreateModel(
                "Van",
                [
                    ("id", models.AutoField(primary_key=True)),
                ]
            ))
        if related_model:
            operations.append(migrations.CreateModel(
                "Rider",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pony", models.ForeignKey("Pony", models.CASCADE)),
                    ("friend", models.ForeignKey("self", models.CASCADE))
                ],
            ))
        if mti_model:
            operations.append(migrations.CreateModel(
                "ShetlandPony",
                fields=[
                    ('pony_ptr', models.OneToOneField(
                        'Pony',
                        models.CASCADE,
                        auto_created=True,
                        parent_link=True,
                        primary_key=True,
                        to_field='id',
                        serialize=False,
                    )),
                    ("cuteness", models.IntegerField(default=1)),
                ],
                bases=['%s.Pony' % app_label],
            ))
        if proxy_model:
            operations.append(migrations.CreateModel(
                "ProxyPony",
                fields=[],
                options={"proxy": True},
                bases=['%s.Pony' % app_label],
            ))
        if manager_model:
            operations.append(migrations.CreateModel(
                "Food",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                ],
                managers=[
                    ("food_qs", FoodQuerySet.as_manager()),
                    ("food_mgr", FoodManager("a", "b")),
                    ("food_mgr_kwargs", FoodManager("x", "y", 3, 4)),
                ]
            ))

        return self.apply_operations(app_label, ProjectState(), operations)


class OperationTests(OperationTestBase):
    """
    Tests running the operations and making sure they do what they say they do.
    Each test looks at their state changing, and then their database operation -
    both forwards and backwards.
    """

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
        self.assertEqual(operation.describe(), "Create model Pony")
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
        self.assertEqual(sorted(definition[2].keys()), ["fields", "name"])
        # And default manager not in set
        operation = migrations.CreateModel("Foo", fields=[], managers=[("objects", models.Manager())])
        definition = operation.deconstruct()
        self.assertNotIn('managers', definition[2])

    def test_create_model_with_duplicate_field_name(self):
        with self.assertRaisesMessage(ValueError, 'Found duplicate value pink in CreateModel fields argument.'):
            migrations.CreateModel(
                "Pony",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pink", models.TextField()),
                    ("pink", models.IntegerField(default=1)),
                ],
            )

    def test_create_model_with_duplicate_base(self):
        message = 'Found duplicate value test_crmo.pony in CreateModel bases argument.'
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=("test_crmo.Pony", "test_crmo.Pony",),
            )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=("test_crmo.Pony", "test_crmo.pony",),
            )
        message = 'Found duplicate value migrations.unicodemodel in CreateModel bases argument.'
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(UnicodeModel, UnicodeModel,),
            )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(UnicodeModel, 'migrations.unicodemodel',),
            )
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(UnicodeModel, 'migrations.UnicodeModel',),
            )
        message = "Found duplicate value <class 'django.db.models.base.Model'> in CreateModel bases argument."
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(models.Model, models.Model,),
            )
        message = "Found duplicate value <class 'migrations.test_operations.Mixin'> in CreateModel bases argument."
        with self.assertRaisesMessage(ValueError, message):
            migrations.CreateModel(
                "Pony",
                fields=[],
                bases=(Mixin, Mixin,),
            )

    def test_create_model_with_duplicate_manager_name(self):
        with self.assertRaisesMessage(ValueError, 'Found duplicate value objects in CreateModel managers argument.'):
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
            operation1.database_forwards("test_crmoua", editor, project_state, new_state)
            project_state, new_state = new_state, new_state.clone()
            operation2.state_forwards("test_crmoua", new_state)
            operation2.database_forwards("test_crmoua", editor, project_state, new_state)
            project_state, new_state = new_state, new_state.clone()
            operation3.state_forwards("test_crmoua", new_state)
            operation3.database_forwards("test_crmoua", editor, project_state, new_state)
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
                ("ponies", models.ManyToManyField("Pony", related_name="stables"))
            ]
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
            operation.database_backwards("test_crmomm", editor, new_state, project_state)
        self.assertTableNotExists("test_crmomm_stable")
        self.assertTableNotExists("test_crmomm_stable_ponies")

    def test_create_model_inheritance(self):
        """
        Tests the CreateModel operation on a multi-table inheritance setup.
        """
        project_state = self.set_up_test_model("test_crmoih")
        # Test the state alteration
        operation = migrations.CreateModel(
            "ShetlandPony",
            [
                ('pony_ptr', models.OneToOneField(
                    'test_crmoih.Pony',
                    models.CASCADE,
                    auto_created=True,
                    primary_key=True,
                    to_field='id',
                    serialize=False,
                )),
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
            operation.database_backwards("test_crmoih", editor, new_state, project_state)
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
            bases=("test_crprmo.Pony", ),
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
            operation.database_backwards("test_crprmo", editor, new_state, project_state)
        self.assertTableNotExists("test_crprmo_proxypony")
        self.assertTableExists("test_crprmo_pony")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "CreateModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2].keys()), ["bases", "fields", "name", "options"])

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
            bases=("test_crummo.Pony", ),
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
            operation.database_backwards("test_crummo", editor, new_state, project_state)
        self.assertTableNotExists("test_crummo_unmanagedpony")
        self.assertTableExists("test_crummo_pony")

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
            ]
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
            operation.database_backwards("test_dlprmo", editor, new_state, project_state)
        self.assertTableExists("test_dlprmo_pony")
        self.assertTableNotExists("test_dlprmo_proxypony")

    def test_rename_model(self):
        """
        Tests the RenameModel operation.
        """
        project_state = self.set_up_test_model("test_rnmo", related_model=True)
        # Test the state alteration
        operation = migrations.RenameModel("Pony", "Horse")
        self.assertEqual(operation.describe(), "Rename model Pony to Horse")
        # Test initial state and database
        self.assertIn(("test_rnmo", "pony"), project_state.models)
        self.assertNotIn(("test_rnmo", "horse"), project_state.models)
        self.assertTableExists("test_rnmo_pony")
        self.assertTableNotExists("test_rnmo_horse")
        if connection.features.supports_foreign_keys:
            self.assertFKExists("test_rnmo_rider", ["pony_id"], ("test_rnmo_pony", "id"))
            self.assertFKNotExists("test_rnmo_rider", ["pony_id"], ("test_rnmo_horse", "id"))
        # Migrate forwards
        new_state = project_state.clone()
        new_state = self.apply_operations("test_rnmo", new_state, [operation])
        # Test new state and database
        self.assertNotIn(("test_rnmo", "pony"), new_state.models)
        self.assertIn(("test_rnmo", "horse"), new_state.models)
        # RenameModel also repoints all incoming FKs and M2Ms
        self.assertEqual("test_rnmo.Horse", new_state.models["test_rnmo", "rider"].fields[1][1].remote_field.model)
        self.assertTableNotExists("test_rnmo_pony")
        self.assertTableExists("test_rnmo_horse")
        if connection.features.supports_foreign_keys:
            self.assertFKNotExists("test_rnmo_rider", ["pony_id"], ("test_rnmo_pony", "id"))
            self.assertFKExists("test_rnmo_rider", ["pony_id"], ("test_rnmo_horse", "id"))
        # Migrate backwards
        original_state = self.unapply_operations("test_rnmo", project_state, [operation])
        # Test original state and database
        self.assertIn(("test_rnmo", "pony"), original_state.models)
        self.assertNotIn(("test_rnmo", "horse"), original_state.models)
        self.assertEqual("Pony", original_state.models["test_rnmo", "rider"].fields[1][1].remote_field.model)
        self.assertTableExists("test_rnmo_pony")
        self.assertTableNotExists("test_rnmo_horse")
        if connection.features.supports_foreign_keys:
            self.assertFKExists("test_rnmo_rider", ["pony_id"], ("test_rnmo_pony", "id"))
            self.assertFKNotExists("test_rnmo_rider", ["pony_id"], ("test_rnmo_horse", "id"))
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RenameModel")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'old_name': "Pony", 'new_name': "Horse"})

    def test_rename_model_state_forwards(self):
        """
        RenameModel operations shouldn't trigger the caching of rendered apps
        on state without prior apps.
        """
        state = ProjectState()
        state.add_model(ModelState('migrations', 'Foo', []))
        operation = migrations.RenameModel('Foo', 'Bar')
        operation.state_forwards('migrations', state)
        self.assertNotIn('apps', state.__dict__)
        self.assertNotIn(('migrations', 'foo'), state.models)
        self.assertIn(('migrations', 'bar'), state.models)
        # Now with apps cached.
        apps = state.apps
        operation = migrations.RenameModel('Bar', 'Foo')
        operation.state_forwards('migrations', state)
        self.assertIs(state.apps, apps)
        self.assertNotIn(('migrations', 'bar'), state.models)
        self.assertIn(('migrations', 'foo'), state.models)

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
            'self',
            new_state.models["test_rmwsrf", "horserider"].fields[2][1].remote_field.model
        )
        HorseRider = new_state.apps.get_model('test_rmwsrf', 'horserider')
        self.assertIs(HorseRider._meta.get_field('horserider').remote_field.model, HorseRider)
        # Test the database alteration
        self.assertTableExists("test_rmwsrf_rider")
        self.assertTableNotExists("test_rmwsrf_horserider")
        if connection.features.supports_foreign_keys:
            self.assertFKExists("test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_rider", "id"))
            self.assertFKNotExists("test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_horserider", "id"))
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rmwsrf", editor, project_state, new_state)
        self.assertTableNotExists("test_rmwsrf_rider")
        self.assertTableExists("test_rmwsrf_horserider")
        if connection.features.supports_foreign_keys:
            self.assertFKNotExists("test_rmwsrf_horserider", ["friend_id"], ("test_rmwsrf_rider", "id"))
            self.assertFKExists("test_rmwsrf_horserider", ["friend_id"], ("test_rmwsrf_horserider", "id"))
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rmwsrf", editor, new_state, project_state)
        self.assertTableExists("test_rmwsrf_rider")
        self.assertTableNotExists("test_rmwsrf_horserider")
        if connection.features.supports_foreign_keys:
            self.assertFKExists("test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_rider", "id"))
            self.assertFKNotExists("test_rmwsrf_rider", ["friend_id"], ("test_rmwsrf_horserider", "id"))

    def test_rename_model_with_superclass_fk(self):
        """
        Tests the RenameModel operation on a model which has a superclass that
        has a foreign key.
        """
        project_state = self.set_up_test_model("test_rmwsc", related_model=True, mti_model=True)
        # Test the state alteration
        operation = migrations.RenameModel("ShetlandPony", "LittleHorse")
        self.assertEqual(operation.describe(), "Rename model ShetlandPony to LittleHorse")
        new_state = project_state.clone()
        operation.state_forwards("test_rmwsc", new_state)
        self.assertNotIn(("test_rmwsc", "shetlandpony"), new_state.models)
        self.assertIn(("test_rmwsc", "littlehorse"), new_state.models)
        # RenameModel shouldn't repoint the superclass's relations, only local ones
        self.assertEqual(
            project_state.models["test_rmwsc", "rider"].fields[1][1].remote_field.model,
            new_state.models["test_rmwsc", "rider"].fields[1][1].remote_field.model
        )
        # Before running the migration we have a table for Shetland Pony, not Little Horse
        self.assertTableExists("test_rmwsc_shetlandpony")
        self.assertTableNotExists("test_rmwsc_littlehorse")
        if connection.features.supports_foreign_keys:
            # and the foreign key on rider points to pony, not shetland pony
            self.assertFKExists("test_rmwsc_rider", ["pony_id"], ("test_rmwsc_pony", "id"))
            self.assertFKNotExists("test_rmwsc_rider", ["pony_id"], ("test_rmwsc_shetlandpony", "id"))
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rmwsc", editor, project_state, new_state)
        # Now we have a little horse table, not shetland pony
        self.assertTableNotExists("test_rmwsc_shetlandpony")
        self.assertTableExists("test_rmwsc_littlehorse")
        if connection.features.supports_foreign_keys:
            # but the Foreign keys still point at pony, not little horse
            self.assertFKExists("test_rmwsc_rider", ["pony_id"], ("test_rmwsc_pony", "id"))
            self.assertFKNotExists("test_rmwsc_rider", ["pony_id"], ("test_rmwsc_littlehorse", "id"))

    def test_rename_model_with_self_referential_m2m(self):
        app_label = "test_rename_model_with_self_referential_m2m"

        project_state = self.apply_operations(app_label, ProjectState(), operations=[
            migrations.CreateModel("ReflexivePony", fields=[
                ("id", models.AutoField(primary_key=True)),
                ("ponies", models.ManyToManyField("self")),
            ]),
        ])
        project_state = self.apply_operations(app_label, project_state, operations=[
            migrations.RenameModel("ReflexivePony", "ReflexivePony2"),
        ])
        Pony = project_state.apps.get_model(app_label, "ReflexivePony2")
        pony = Pony.objects.create()
        pony.ponies.add(pony)

    def test_rename_model_with_m2m(self):
        app_label = "test_rename_model_with_m2m"
        project_state = self.apply_operations(app_label, ProjectState(), operations=[
            migrations.CreateModel("Rider", fields=[
                ("id", models.AutoField(primary_key=True)),
            ]),
            migrations.CreateModel("Pony", fields=[
                ("id", models.AutoField(primary_key=True)),
                ("riders", models.ManyToManyField("Rider")),
            ]),
        ])
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)

        project_state = self.apply_operations(app_label, project_state, operations=[
            migrations.RenameModel("Pony", "Pony2"),
        ])
        Pony = project_state.apps.get_model(app_label, "Pony2")
        Rider = project_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)
        self.assertEqual(Pony.objects.count(), 2)
        self.assertEqual(Rider.objects.count(), 2)
        self.assertEqual(Pony._meta.get_field('riders').remote_field.through.objects.count(), 2)

    def test_rename_m2m_target_model(self):
        app_label = "test_rename_m2m_target_model"
        project_state = self.apply_operations(app_label, ProjectState(), operations=[
            migrations.CreateModel("Rider", fields=[
                ("id", models.AutoField(primary_key=True)),
            ]),
            migrations.CreateModel("Pony", fields=[
                ("id", models.AutoField(primary_key=True)),
                ("riders", models.ManyToManyField("Rider")),
            ]),
        ])
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)

        project_state = self.apply_operations(app_label, project_state, operations=[
            migrations.RenameModel("Rider", "Rider2"),
        ])
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider2")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        pony.riders.add(rider)
        self.assertEqual(Pony.objects.count(), 2)
        self.assertEqual(Rider.objects.count(), 2)
        self.assertEqual(Pony._meta.get_field('riders').remote_field.through.objects.count(), 2)

    def test_rename_m2m_through_model(self):
        app_label = "test_rename_through"
        project_state = self.apply_operations(app_label, ProjectState(), operations=[
            migrations.CreateModel("Rider", fields=[
                ("id", models.AutoField(primary_key=True)),
            ]),
            migrations.CreateModel("Pony", fields=[
                ("id", models.AutoField(primary_key=True)),
            ]),
            migrations.CreateModel("PonyRider", fields=[
                ("id", models.AutoField(primary_key=True)),
                ("rider", models.ForeignKey("test_rename_through.Rider", models.CASCADE)),
                ("pony", models.ForeignKey("test_rename_through.Pony", models.CASCADE)),
            ]),
            migrations.AddField(
                "Pony",
                "riders",
                models.ManyToManyField("test_rename_through.Rider", through="test_rename_through.PonyRider"),
            ),
        ])
        Pony = project_state.apps.get_model(app_label, "Pony")
        Rider = project_state.apps.get_model(app_label, "Rider")
        PonyRider = project_state.apps.get_model(app_label, "PonyRider")
        pony = Pony.objects.create()
        rider = Rider.objects.create()
        PonyRider.objects.create(pony=pony, rider=rider)

        project_state = self.apply_operations(app_label, project_state, operations=[
            migrations.RenameModel("PonyRider", "PonyRider2"),
        ])
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
        project_state, new_state = self.make_test_state("test_adfl", operation)
        self.assertEqual(len(new_state.models["test_adfl", "pony"].fields), 4)
        field = [
            f for n, f in new_state.models["test_adfl", "pony"].fields
            if n == "height"
        ][0]
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

        new_state = self.apply_operations("test_adchfl", project_state, [
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
        ])

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

        new_state = self.apply_operations("test_adtxtfl", project_state, [
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
        ])

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

        new_state = self.apply_operations("test_adbinfl", project_state, [
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
        ])

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
            operation.database_forwards("test_regr22168", editor, project_state, new_state)
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
        self.assertEqual(len(new_state.models["test_adflpd", "pony"].fields), 4)
        field = [
            f for n, f in new_state.models["test_adflpd", "pony"].fields
            if n == "height"
        ][0]
        self.assertEqual(field.default, NOT_PROVIDED)
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
        self.assertEqual(sorted(definition[2]), ["field", "model_name", "name", "preserve_default"])

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
            Pony = new_state.apps.get_model("test_adflmm", "Pony")
            p = Pony.objects.create(pink=False, weight=4.55)
            p.stables.create()
            self.assertEqual(p.stables.count(), 1)
            p.stables.all().delete()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adflmm", editor, new_state, project_state)
        self.assertTableNotExists("test_adflmm_pony_stables")

    def test_alter_field_m2m(self):
        project_state = self.set_up_test_model("test_alflmm", second_model=True)

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies"))
        ])
        Pony = project_state.apps.get_model("test_alflmm", "Pony")
        self.assertFalse(Pony._meta.get_field('stables').blank)

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AlterField(
                "Pony", "stables", models.ManyToManyField(to="Stable", related_name="ponies", blank=True)
            )
        ])
        Pony = project_state.apps.get_model("test_alflmm", "Pony")
        self.assertTrue(Pony._meta.get_field('stables').blank)

    def test_repoint_field_m2m(self):
        project_state = self.set_up_test_model("test_alflmm", second_model=True, third_model=True)

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AddField("Pony", "places", models.ManyToManyField("Stable", related_name="ponies"))
        ])
        Pony = project_state.apps.get_model("test_alflmm", "Pony")

        project_state = self.apply_operations("test_alflmm", project_state, operations=[
            migrations.AlterField("Pony", "places", models.ManyToManyField(to="Van", related_name="ponies"))
        ])

        # Ensure the new field actually works
        Pony = project_state.apps.get_model("test_alflmm", "Pony")
        p = Pony.objects.create(pink=False, weight=4.55)
        p.places.create()
        self.assertEqual(p.places.count(), 1)
        p.places.all().delete()

    def test_remove_field_m2m(self):
        project_state = self.set_up_test_model("test_rmflmm", second_model=True)

        project_state = self.apply_operations("test_rmflmm", project_state, operations=[
            migrations.AddField("Pony", "stables", models.ManyToManyField("Stable", related_name="ponies"))
        ])
        self.assertTableExists("test_rmflmm_pony_stables")

        with_field_state = project_state.clone()
        operations = [migrations.RemoveField("Pony", "stables")]
        project_state = self.apply_operations("test_rmflmm", project_state, operations=operations)
        self.assertTableNotExists("test_rmflmm_pony_stables")

        # And test reversal
        self.unapply_operations("test_rmflmm", with_field_state, operations=operations)
        self.assertTableExists("test_rmflmm_pony_stables")

    def test_remove_field_m2m_with_through(self):
        project_state = self.set_up_test_model("test_rmflmmwt", second_model=True)

        self.assertTableNotExists("test_rmflmmwt_ponystables")
        project_state = self.apply_operations("test_rmflmmwt", project_state, operations=[
            migrations.CreateModel("PonyStables", fields=[
                ("pony", models.ForeignKey('test_rmflmmwt.Pony', models.CASCADE)),
                ("stable", models.ForeignKey('test_rmflmmwt.Stable', models.CASCADE)),
            ]),
            migrations.AddField(
                "Pony", "stables",
                models.ManyToManyField("Stable", related_name="ponies", through='test_rmflmmwt.PonyStables')
            )
        ])
        self.assertTableExists("test_rmflmmwt_ponystables")

        operations = [migrations.RemoveField("Pony", "stables")]
        self.apply_operations("test_rmflmmwt", project_state, operations=operations)

    def test_remove_field(self):
        """
        Tests the RemoveField operation.
        """
        project_state = self.set_up_test_model("test_rmfl")
        # Test the state alteration
        operation = migrations.RemoveField("Pony", "pink")
        self.assertEqual(operation.describe(), "Remove field pink from Pony")
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
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveField")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'model_name': "Pony", 'name': 'pink'})

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
        self.assertEqual(operation.describe(), "Rename table for Pony to test_almota_pony_2")
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
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelTable")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'name': "Pony", 'table': "test_almota_pony_2"})

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
        self.assertEqual(new_state.models["test_almota", "pony"].options["db_table"], "test_almota_pony")
        # Test the database alteration
        self.assertTableExists("test_almota_pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_almota", editor, project_state, new_state)
        self.assertTableExists("test_almota_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_almota", editor, new_state, project_state)
        self.assertTableExists("test_almota_pony")

    def test_alter_model_table_m2m(self):
        """
        AlterModelTable should rename auto-generated M2M tables.
        """
        app_label = "test_talflmltlm2m"
        pony_db_table = 'pony_foo'
        project_state = self.set_up_test_model(app_label, second_model=True, db_table=pony_db_table)
        # Add the M2M field
        first_state = project_state.clone()
        operation = migrations.AddField("Pony", "stables", models.ManyToManyField("Stable"))
        operation.state_forwards(app_label, first_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, project_state, first_state)
        original_m2m_table = "%s_%s" % (pony_db_table, "stables")
        new_m2m_table = "%s_%s" % (app_label, "pony_stables")
        self.assertTableExists(original_m2m_table)
        self.assertTableNotExists(new_m2m_table)
        # Rename the Pony db_table which should also rename the m2m table.
        second_state = first_state.clone()
        operation = migrations.AlterModelTable(name='pony', table=None)
        operation.state_forwards(app_label, second_state)
        with connection.schema_editor() as editor:
            operation.database_forwards(app_label, editor, first_state, second_state)
        self.assertTableExists(new_m2m_table)
        self.assertTableNotExists(original_m2m_table)
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, second_state, first_state)
        self.assertTableExists(original_m2m_table)
        self.assertTableNotExists(new_m2m_table)

    def test_alter_field(self):
        """
        Tests the AlterField operation.
        """
        project_state = self.set_up_test_model("test_alfl")
        # Test the state alteration
        operation = migrations.AlterField("Pony", "pink", models.IntegerField(null=True))
        self.assertEqual(operation.describe(), "Alter field pink on Pony")
        new_state = project_state.clone()
        operation.state_forwards("test_alfl", new_state)
        self.assertIs(project_state.models["test_alfl", "pony"].get_field_by_name("pink").null, False)
        self.assertIs(new_state.models["test_alfl", "pony"].get_field_by_name("pink").null, True)
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

    def test_alter_field_pk(self):
        """
        Tests the AlterField operation on primary keys (for things like PostgreSQL's SERIAL weirdness)
        """
        project_state = self.set_up_test_model("test_alflpk")
        # Test the state alteration
        operation = migrations.AlterField("Pony", "id", models.IntegerField(primary_key=True))
        new_state = project_state.clone()
        operation.state_forwards("test_alflpk", new_state)
        self.assertIsInstance(project_state.models["test_alflpk", "pony"].get_field_by_name("id"), models.AutoField)
        self.assertIsInstance(new_state.models["test_alflpk", "pony"].get_field_by_name("id"), models.IntegerField)
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alflpk", editor, project_state, new_state)
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alflpk", editor, new_state, project_state)

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_alter_field_pk_fk(self):
        """
        Tests the AlterField operation on primary keys changes any FKs pointing to it.
        """
        project_state = self.set_up_test_model("test_alflpkfk", related_model=True)
        # Test the state alteration
        operation = migrations.AlterField("Pony", "id", models.FloatField(primary_key=True))
        new_state = project_state.clone()
        operation.state_forwards("test_alflpkfk", new_state)
        self.assertIsInstance(project_state.models["test_alflpkfk", "pony"].get_field_by_name("id"), models.AutoField)
        self.assertIsInstance(new_state.models["test_alflpkfk", "pony"].get_field_by_name("id"), models.FloatField)

        def assertIdTypeEqualsFkType():
            with connection.cursor() as cursor:
                id_type, id_null = [
                    (c.type_code, c.null_ok)
                    for c in connection.introspection.get_table_description(cursor, "test_alflpkfk_pony")
                    if c.name == "id"
                ][0]
                fk_type, fk_null = [
                    (c.type_code, c.null_ok)
                    for c in connection.introspection.get_table_description(cursor, "test_alflpkfk_rider")
                    if c.name == "pony_id"
                ][0]
            self.assertEqual(id_type, fk_type)
            self.assertEqual(id_null, fk_null)

        assertIdTypeEqualsFkType()
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alflpkfk", editor, project_state, new_state)
        assertIdTypeEqualsFkType()
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alflpkfk", editor, new_state, project_state)
        assertIdTypeEqualsFkType()

    def test_rename_field(self):
        """
        Tests the RenameField operation.
        """
        project_state = self.set_up_test_model("test_rnfl", unique_together=True, index_together=True)
        # Test the state alteration
        operation = migrations.RenameField("Pony", "pink", "blue")
        self.assertEqual(operation.describe(), "Rename field pink on Pony to blue")
        new_state = project_state.clone()
        operation.state_forwards("test_rnfl", new_state)
        self.assertIn("blue", [n for n, f in new_state.models["test_rnfl", "pony"].fields])
        self.assertNotIn("pink", [n for n, f in new_state.models["test_rnfl", "pony"].fields])
        # Make sure the unique_together has the renamed column too
        self.assertIn("blue", new_state.models["test_rnfl", "pony"].options['unique_together'][0])
        self.assertNotIn("pink", new_state.models["test_rnfl", "pony"].options['unique_together'][0])
        # Make sure the index_together has the renamed column too
        self.assertIn("blue", new_state.models["test_rnfl", "pony"].options['index_together'][0])
        self.assertNotIn("pink", new_state.models["test_rnfl", "pony"].options['index_together'][0])
        # Test the database alteration
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_rnfl", editor, project_state, new_state)
        self.assertColumnExists("test_rnfl_pony", "blue")
        self.assertColumnNotExists("test_rnfl_pony", "pink")
        # Ensure the unique constraint has been ported over
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO test_rnfl_pony (blue, weight) VALUES (1, 1)")
            with self.assertRaises(IntegrityError):
                with atomic():
                    cursor.execute("INSERT INTO test_rnfl_pony (blue, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_rnfl_pony")
        # Ensure the index constraint has been ported over
        self.assertIndexExists("test_rnfl_pony", ["weight", "blue"])
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_rnfl", editor, new_state, project_state)
        self.assertColumnExists("test_rnfl_pony", "pink")
        self.assertColumnNotExists("test_rnfl_pony", "blue")
        # Ensure the index constraint has been reset
        self.assertIndexExists("test_rnfl_pony", ["weight", "pink"])
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RenameField")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'model_name': "Pony", 'old_name': "pink", 'new_name': "blue"})

    def test_alter_unique_together(self):
        """
        Tests the AlterUniqueTogether operation.
        """
        project_state = self.set_up_test_model("test_alunto")
        # Test the state alteration
        operation = migrations.AlterUniqueTogether("Pony", [("pink", "weight")])
        self.assertEqual(operation.describe(), "Alter unique_together for Pony (1 constraint(s))")
        new_state = project_state.clone()
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(len(project_state.models["test_alunto", "pony"].options.get("unique_together", set())), 0)
        self.assertEqual(len(new_state.models["test_alunto", "pony"].options.get("unique_together", set())), 1)
        # Make sure we can insert duplicate rows
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
            # Test the database alteration
            with connection.schema_editor() as editor:
                operation.database_forwards("test_alunto", editor, project_state, new_state)
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            with self.assertRaises(IntegrityError):
                with atomic():
                    cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
            # And test reversal
            with connection.schema_editor() as editor:
                operation.database_backwards("test_alunto", editor, new_state, project_state)
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("INSERT INTO test_alunto_pony (pink, weight) VALUES (1, 1)")
            cursor.execute("DELETE FROM test_alunto_pony")
        # Test flat unique_together
        operation = migrations.AlterUniqueTogether("Pony", ("pink", "weight"))
        operation.state_forwards("test_alunto", new_state)
        self.assertEqual(len(new_state.models["test_alunto", "pony"].options.get("unique_together", set())), 1)
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterUniqueTogether")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'name': "Pony", 'unique_together': {("pink", "weight")}})

    def test_alter_unique_together_remove(self):
        operation = migrations.AlterUniqueTogether("Pony", None)
        self.assertEqual(operation.describe(), "Alter unique_together for Pony (0 constraint(s))")

    def test_add_index(self):
        """
        Test the AddIndex operation.
        """
        project_state = self.set_up_test_model("test_adin")
        msg = (
            "Indexes passed to AddIndex operations require a name argument. "
            "<Index: fields='pink'> doesn't have one."
        )
        with self.assertRaisesMessage(ValueError, msg):
            migrations.AddIndex("Pony", models.Index(fields=["pink"]))
        index = models.Index(fields=["pink"], name="test_adin_pony_pink_idx")
        operation = migrations.AddIndex("Pony", index)
        self.assertEqual(operation.describe(), "Create index test_adin_pony_pink_idx on field(s) pink of model Pony")
        new_state = project_state.clone()
        operation.state_forwards("test_adin", new_state)
        # Test the database alteration
        self.assertEqual(len(new_state.models["test_adin", "pony"].options['indexes']), 1)
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
        self.assertEqual(definition[2], {'model_name': "Pony", 'index': index})

    def test_remove_index(self):
        """
        Test the RemoveIndex operation.
        """
        project_state = self.set_up_test_model("test_rmin", multicol_index=True)
        self.assertTableExists("test_rmin_pony")
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])
        operation = migrations.RemoveIndex("Pony", "pony_test_idx")
        self.assertEqual(operation.describe(), "Remove index pony_test_idx from Pony")
        new_state = project_state.clone()
        operation.state_forwards("test_rmin", new_state)
        # Test the state alteration
        self.assertEqual(len(new_state.models["test_rmin", "pony"].options['indexes']), 0)
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
        self.assertEqual(definition[2], {'model_name': "Pony", 'name': "pony_test_idx"})

        # Also test a field dropped with index - sqlite remake issue
        operations = [
            migrations.RemoveIndex("Pony", "pony_test_idx"),
            migrations.RemoveField("Pony", "pink"),
        ]
        self.assertColumnExists("test_rmin_pony", "pink")
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])
        # Test database alteration
        new_state = project_state.clone()
        self.apply_operations('test_rmin', new_state, operations=operations)
        self.assertColumnNotExists("test_rmin_pony", "pink")
        self.assertIndexNotExists("test_rmin_pony", ["pink", "weight"])
        # And test reversal
        self.unapply_operations("test_rmin", project_state, operations=operations)
        self.assertIndexExists("test_rmin_pony", ["pink", "weight"])

    def test_alter_field_with_index(self):
        """
        Test AlterField operation with an index to ensure indexes created via
        Meta.indexes don't get dropped with sqlite3 remake.
        """
        project_state = self.set_up_test_model("test_alflin", index=True)
        operation = migrations.AlterField("Pony", "pink", models.IntegerField(null=True))
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
            operation.database_backwards("test_alflin", editor, new_state, project_state)
        # Ensure the index is still there
        self.assertIndexExists("test_alflin_pony", ["pink"])

    def test_alter_index_together(self):
        """
        Tests the AlterIndexTogether operation.
        """
        project_state = self.set_up_test_model("test_alinto")
        # Test the state alteration
        operation = migrations.AlterIndexTogether("Pony", [("pink", "weight")])
        self.assertEqual(operation.describe(), "Alter index_together for Pony (1 constraint(s))")
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
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterIndexTogether")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'name': "Pony", 'index_together': {("pink", "weight")}})

    def test_alter_index_together_remove(self):
        operation = migrations.AlterIndexTogether("Pony", None)
        self.assertEqual(operation.describe(), "Alter index_together for Pony (0 constraint(s))")

    def test_alter_model_options(self):
        """
        Tests the AlterModelOptions operation.
        """
        project_state = self.set_up_test_model("test_almoop")
        # Test the state alteration (no DB alteration to test)
        operation = migrations.AlterModelOptions("Pony", {"permissions": [("can_groom", "Can groom")]})
        self.assertEqual(operation.describe(), "Change Meta options on Pony")
        new_state = project_state.clone()
        operation.state_forwards("test_almoop", new_state)
        self.assertEqual(len(project_state.models["test_almoop", "pony"].options.get("permissions", [])), 0)
        self.assertEqual(len(new_state.models["test_almoop", "pony"].options.get("permissions", [])), 1)
        self.assertEqual(new_state.models["test_almoop", "pony"].options["permissions"][0][0], "can_groom")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelOptions")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'name': "Pony", 'options': {"permissions": [("can_groom", "Can groom")]}})

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
        self.assertEqual(len(project_state.models["test_almoop", "pony"].options.get("permissions", [])), 1)
        self.assertEqual(len(new_state.models["test_almoop", "pony"].options.get("permissions", [])), 0)
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterModelOptions")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'name': "Pony", 'options': {}})

    def test_alter_order_with_respect_to(self):
        """
        Tests the AlterOrderWithRespectTo operation.
        """
        project_state = self.set_up_test_model("test_alorwrtto", related_model=True)
        # Test the state alteration
        operation = migrations.AlterOrderWithRespectTo("Rider", "pony")
        self.assertEqual(operation.describe(), "Set order_with_respect_to on Rider to pony")
        new_state = project_state.clone()
        operation.state_forwards("test_alorwrtto", new_state)
        self.assertIsNone(
            project_state.models["test_alorwrtto", "rider"].options.get("order_with_respect_to", None)
        )
        self.assertEqual(
            new_state.models["test_alorwrtto", "rider"].options.get("order_with_respect_to", None),
            "pony"
        )
        # Make sure there's no matching index
        self.assertColumnNotExists("test_alorwrtto_rider", "_order")
        # Create some rows before alteration
        rendered_state = project_state.apps
        pony = rendered_state.get_model("test_alorwrtto", "Pony").objects.create(weight=50)
        rendered_state.get_model("test_alorwrtto", "Rider").objects.create(pony=pony, friend_id=1)
        rendered_state.get_model("test_alorwrtto", "Rider").objects.create(pony=pony, friend_id=2)
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_alorwrtto", editor, project_state, new_state)
        self.assertColumnExists("test_alorwrtto_rider", "_order")
        # Check for correct value in rows
        updated_riders = new_state.apps.get_model("test_alorwrtto", "Rider").objects.all()
        self.assertEqual(updated_riders[0]._order, 0)
        self.assertEqual(updated_riders[1]._order, 0)
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_alorwrtto", editor, new_state, project_state)
        self.assertColumnNotExists("test_alorwrtto_rider", "_order")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "AlterOrderWithRespectTo")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {'name': "Rider", 'order_with_respect_to': "pony"})

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
            ]
        )
        self.assertEqual(operation.describe(), "Change managers on Pony")
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
        model = rendered_state.get_model('test_almoma', 'pony')
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
            model_name='Rider',
            name='pony',
            field=models.ForeignKey("Pony", models.CASCADE, editable=False),
        )
        alter_state = create_state.clone()
        alter_operation.state_forwards("test_alfk", alter_state)
        with connection.schema_editor() as editor:
            create_operation.database_forwards("test_alfk", editor, project_state, create_state)
            alter_operation.database_forwards("test_alfk", editor, create_state, alter_state)

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
        project_state, new_state = self.make_test_state("test_afknfk", operation, related_model=True)
        # Test the database alteration
        self.assertColumnExists("test_afknfk_rider", "pony_id")
        self.assertColumnNotExists("test_afknfk_rider", "pony")
        with connection.schema_editor() as editor:
            operation.database_forwards("test_afknfk", editor, project_state, new_state)
        self.assertColumnExists("test_afknfk_rider", "pony")
        self.assertColumnNotExists("test_afknfk_rider", "pony_id")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_afknfk", editor, new_state, project_state)
        self.assertColumnExists("test_afknfk_rider", "pony_id")
        self.assertColumnNotExists("test_afknfk_rider", "pony")

    @unittest.skipIf(sqlparse is None and connection.features.requires_sqlparse_for_splitting, "Missing sqlparse")
    def test_run_sql(self):
        """
        Tests the RunSQL operation.
        """
        project_state = self.set_up_test_model("test_runsql")
        # Create the operation
        operation = migrations.RunSQL(
            # Use a multi-line string with a comment to test splitting on SQLite and MySQL respectively
            "CREATE TABLE i_love_ponies (id int, special_thing varchar(15));\n"
            "INSERT INTO i_love_ponies (id, special_thing) VALUES (1, 'i love ponies'); -- this is magic!\n"
            "INSERT INTO i_love_ponies (id, special_thing) VALUES (2, 'i love django');\n"
            "UPDATE i_love_ponies SET special_thing = 'Ponies' WHERE special_thing LIKE '%%ponies';"
            "UPDATE i_love_ponies SET special_thing = 'Django' WHERE special_thing LIKE '%django';",

            # Run delete queries to test for parameter substitution failure
            # reported in #23426
            "DELETE FROM i_love_ponies WHERE special_thing LIKE '%Django%';"
            "DELETE FROM i_love_ponies WHERE special_thing LIKE '%%Ponies%%';"
            "DROP TABLE i_love_ponies",

            state_operations=[migrations.CreateModel("SomethingElse", [("id", models.AutoField(primary_key=True))])],
        )
        self.assertEqual(operation.describe(), "Raw SQL operation")
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_runsql", new_state)
        self.assertEqual(len(new_state.models["test_runsql", "somethingelse"].fields), 1)
        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        # Test SQL collection
        with connection.schema_editor(collect_sql=True) as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)
            self.assertIn("LIKE '%%ponies';", "\n".join(editor.collected_sql))
            operation.database_backwards("test_runsql", editor, project_state, new_state)
            self.assertIn("LIKE '%%Ponies%%';", "\n".join(editor.collected_sql))
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)
        self.assertTableExists("i_love_ponies")
        # Make sure all the SQL was processed
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 2)
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies WHERE special_thing = 'Django'")
            self.assertEqual(cursor.fetchall()[0][0], 1)
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies WHERE special_thing = 'Ponies'")
            self.assertEqual(cursor.fetchall()[0][0], 1)
        # And test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards("test_runsql", editor, new_state, project_state)
        self.assertTableNotExists("i_love_ponies")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RunSQL")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["reverse_sql", "sql", "state_operations"])
        # And elidable reduction
        self.assertIs(False, operation.reduce(operation, []))
        elidable_operation = migrations.RunSQL('SELECT 1 FROM void;', elidable=True)
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
                ["INSERT INTO i_love_ponies (id, special_thing) VALUES (2, %s);", ['Ponies']],
                ("INSERT INTO i_love_ponies (id, special_thing) VALUES (%s, %s);", (3, 'Python',)),
            ),
            # backwards
            [
                "DELETE FROM i_love_ponies WHERE special_thing = 'Django';",
                ["DELETE FROM i_love_ponies WHERE special_thing = 'Ponies';", None],
                ("DELETE FROM i_love_ponies WHERE id = %s OR special_thing = %s;", [3, 'Python']),
            ]
        )

        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        new_state = project_state.clone()
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, project_state, new_state)

        # Test parameter passing
        with connection.schema_editor() as editor:
            param_operation.database_forwards("test_runsql", editor, project_state, new_state)
        # Make sure all the SQL was processed
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 3)

        with connection.schema_editor() as editor:
            param_operation.database_backwards("test_runsql", editor, new_state, project_state)
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM i_love_ponies")
            self.assertEqual(cursor.fetchall()[0][0], 0)

        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_runsql", editor, new_state, project_state)
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
            [
                ["INSERT INTO foo (bar) VALUES ('buz');"]
            ],
            # backwards
            (
                ("DELETE FROM foo WHERE bar = 'buz';", 'invalid', 'parameter count'),
            ),
        )

        with connection.schema_editor() as editor:
            with self.assertRaisesMessage(ValueError, "Expected a 2-tuple but got 1"):
                operation.database_forwards("test_runsql", editor, project_state, new_state)

        with connection.schema_editor() as editor:
            with self.assertRaisesMessage(ValueError, "Expected a 2-tuple but got 3"):
                operation.database_backwards("test_runsql", editor, new_state, project_state)

    def test_run_sql_noop(self):
        """
        #24098 - Tests no-op RunSQL operations.
        """
        operation = migrations.RunSQL(migrations.RunSQL.noop, migrations.RunSQL.noop)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runsql", editor, None, None)
            operation.database_backwards("test_runsql", editor, None, None)

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
        operation = migrations.RunPython(inner_method, reverse_code=inner_method_reverse)
        self.assertEqual(operation.describe(), "Raw Python operation")
        # Test the state alteration does nothing
        new_state = project_state.clone()
        operation.state_forwards("test_runpython", new_state)
        self.assertEqual(new_state, project_state)
        # Test the database alteration
        self.assertEqual(project_state.apps.get_model("test_runpython", "Pony").objects.count(), 0)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.apps.get_model("test_runpython", "Pony").objects.count(), 2)
        # Now test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.apps.get_model("test_runpython", "Pony").objects.count(), 0)
        # Now test we can't use a string
        with self.assertRaises(ValueError):
            migrations.RunPython("print 'ahahaha'")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RunPython")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["code", "reverse_code"])

        # Also test reversal fails, with an operation identical to above but without reverse_code set
        no_reverse_operation = migrations.RunPython(inner_method)
        self.assertFalse(no_reverse_operation.reversible)
        with connection.schema_editor() as editor:
            no_reverse_operation.database_forwards("test_runpython", editor, project_state, new_state)
            with self.assertRaises(NotImplementedError):
                no_reverse_operation.database_backwards("test_runpython", editor, new_state, project_state)
        self.assertEqual(project_state.apps.get_model("test_runpython", "Pony").objects.count(), 2)

        def create_ponies(models, schema_editor):
            Pony = models.get_model("test_runpython", "Pony")
            pony1 = Pony.objects.create(pink=1, weight=3.55)
            self.assertIsNot(pony1.pk, None)
            pony2 = Pony.objects.create(weight=5)
            self.assertIsNot(pony2.pk, None)
            self.assertNotEqual(pony1.pk, pony2.pk)

        operation = migrations.RunPython(create_ponies)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.apps.get_model("test_runpython", "Pony").objects.count(), 4)
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
            operation.database_forwards("test_runpython", editor, project_state, new_state)
        self.assertEqual(project_state.apps.get_model("test_runpython", "Pony").objects.count(), 6)
        self.assertEqual(project_state.apps.get_model("test_runpython", "ShetlandPony").objects.count(), 2)
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

        atomic_migration = Migration("test", "test_runpythonatomic")
        atomic_migration.operations = [migrations.RunPython(inner_method)]
        non_atomic_migration = Migration("test", "test_runpythonatomic")
        non_atomic_migration.operations = [migrations.RunPython(inner_method, atomic=False)]
        # If we're a fully-transactional database, both versions should rollback
        if connection.features.can_rollback_ddl:
            self.assertEqual(project_state.apps.get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.apps.get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.apps.get_model("test_runpythonatomic", "Pony").objects.count(), 0)
        # Otherwise, the non-atomic operation should leave a row there
        else:
            self.assertEqual(project_state.apps.get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.apps.get_model("test_runpythonatomic", "Pony").objects.count(), 0)
            with self.assertRaises(ValueError):
                with connection.schema_editor() as editor:
                    non_atomic_migration.apply(project_state, editor)
            self.assertEqual(project_state.apps.get_model("test_runpythonatomic", "Pony").objects.count(), 1)
        # And deconstruction
        definition = non_atomic_migration.operations[0].deconstruct()
        self.assertEqual(definition[0], "RunPython")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["atomic", "code"])

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
                ("author", models.ForeignKey("test_authors.Author", models.CASCADE))
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
            create_author.database_forwards("test_authors", editor, project_state, new_state)
        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_book.state_forwards("test_books", new_state)
            create_book.database_forwards("test_books", editor, project_state, new_state)
        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            add_hometown.state_forwards("test_authors", new_state)
            add_hometown.database_forwards("test_authors", editor, project_state, new_state)
        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_old_man.state_forwards("test_books", new_state)
            create_old_man.database_forwards("test_books", editor, project_state, new_state)

    def test_model_with_bigautofield(self):
        """
        A model with BigAutoField can be created.
        """
        def create_data(models, schema_editor):
            Author = models.get_model("test_author", "Author")
            Book = models.get_model("test_book", "Book")
            author1 = Author.objects.create(name="Hemingway")
            Book.objects.create(title="Old Man and The Sea", author=author1)
            Book.objects.create(id=2 ** 33, title="A farewell to arms", author=author1)

            author2 = Author.objects.create(id=2 ** 33, name="Remarque")
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
                ("author", models.ForeignKey(to="test_author.Author", on_delete=models.CASCADE))
            ],
            options={},
        )
        fill_data = migrations.RunPython(create_data)

        project_state = ProjectState()
        new_state = project_state.clone()
        with connection.schema_editor() as editor:
            create_author.state_forwards("test_author", new_state)
            create_author.database_forwards("test_author", editor, project_state, new_state)

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

    def test_autofield_foreignfield_growth(self):
        """
        A field may be migrated from AutoField to BigAutoField.
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
            blog2 = Blog.objects.create(name="Frameworks", id=2 ** 33)
            Article.objects.create(name="Django", blog=blog2)
            Article.objects.create(id=2 ** 33, name="Django2", blog=blog2)

        create_blog = migrations.CreateModel(
            "Blog",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={},
        )
        create_article = migrations.CreateModel(
            "Article",
            [
                ("id", models.AutoField(primary_key=True)),
                ("blog", models.ForeignKey(to="test_blog.Blog", on_delete=models.CASCADE)),
                ("name", models.CharField(max_length=100)),
                ("data", models.TextField(default="")),
            ],
            options={},
        )
        fill_initial_data = migrations.RunPython(create_initial_data, create_initial_data)
        fill_big_data = migrations.RunPython(create_big_data, create_big_data)

        grow_article_id = migrations.AlterField("Article", "id", models.BigAutoField(primary_key=True))
        grow_blog_id = migrations.AlterField("Blog", "id", models.BigAutoField(primary_key=True))

        project_state = ProjectState()
        new_state = project_state.clone()
        with connection.schema_editor() as editor:
            create_blog.state_forwards("test_blog", new_state)
            create_blog.database_forwards("test_blog", editor, project_state, new_state)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            create_article.state_forwards("test_article", new_state)
            create_article.database_forwards("test_article", editor, project_state, new_state)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            fill_initial_data.state_forwards("fill_initial_data", new_state)
            fill_initial_data.database_forwards("fill_initial_data", editor, project_state, new_state)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            grow_article_id.state_forwards("test_article", new_state)
            grow_article_id.database_forwards("test_article", editor, project_state, new_state)

        state = new_state.clone()
        article = state.apps.get_model("test_article.Article")
        self.assertIsInstance(article._meta.pk, models.BigAutoField)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            grow_blog_id.state_forwards("test_blog", new_state)
            grow_blog_id.database_forwards("test_blog", editor, project_state, new_state)

        state = new_state.clone()
        blog = state.apps.get_model("test_blog.Blog")
        self.assertIsInstance(blog._meta.pk, models.BigAutoField)

        project_state = new_state
        new_state = new_state.clone()
        with connection.schema_editor() as editor:
            fill_big_data.state_forwards("fill_big_data", new_state)
            fill_big_data.database_forwards("fill_big_data", editor, project_state, new_state)

    def test_run_python_noop(self):
        """
        #24098 - Tests no-op RunPython operations.
        """
        project_state = ProjectState()
        new_state = project_state.clone()
        operation = migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_runpython", editor, project_state, new_state)
            operation.database_backwards("test_runpython", editor, new_state, project_state)

    @unittest.skipIf(sqlparse is None and connection.features.requires_sqlparse_for_splitting, "Missing sqlparse")
    def test_separate_database_and_state(self):
        """
        Tests the SeparateDatabaseAndState operation.
        """
        project_state = self.set_up_test_model("test_separatedatabaseandstate")
        # Create the operation
        database_operation = migrations.RunSQL(
            "CREATE TABLE i_love_ponies (id int, special_thing int);",
            "DROP TABLE i_love_ponies;"
        )
        state_operation = migrations.CreateModel("SomethingElse", [("id", models.AutoField(primary_key=True))])
        operation = migrations.SeparateDatabaseAndState(
            state_operations=[state_operation],
            database_operations=[database_operation]
        )
        self.assertEqual(operation.describe(), "Custom state/database change combination")
        # Test the state alteration
        new_state = project_state.clone()
        operation.state_forwards("test_separatedatabaseandstate", new_state)
        self.assertEqual(len(new_state.models["test_separatedatabaseandstate", "somethingelse"].fields), 1)
        # Make sure there's no table
        self.assertTableNotExists("i_love_ponies")
        # Test the database alteration
        with connection.schema_editor() as editor:
            operation.database_forwards("test_separatedatabaseandstate", editor, project_state, new_state)
        self.assertTableExists("i_love_ponies")
        # And test reversal
        self.assertTrue(operation.reversible)
        with connection.schema_editor() as editor:
            operation.database_backwards("test_separatedatabaseandstate", editor, new_state, project_state)
        self.assertTableNotExists("i_love_ponies")
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "SeparateDatabaseAndState")
        self.assertEqual(definition[1], [])
        self.assertEqual(sorted(definition[2]), ["database_operations", "state_operations"])

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
            self.assertEqual(len(new_state.models[app_label, "somethingcompletelydifferent"].fields), 1)
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

    available_apps = ['migrations']

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
            operation.database_backwards("test_crigsw", editor, new_state, project_state)
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
            operation.database_backwards("test_dligsw", editor, new_state, project_state)
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
            operation.database_forwards("test_adfligsw", editor, project_state, new_state)
        self.assertTableNotExists("test_adfligsw_pony")
        # And test reversal
        with connection.schema_editor() as editor:
            operation.database_backwards("test_adfligsw", editor, new_state, project_state)
        self.assertTableNotExists("test_adfligsw_pony")

    @override_settings(TEST_SWAP_MODEL='migrations.SomeFakeModel')
    def test_indexes_ignore_swapped(self):
        """
        Add/RemoveIndex operations ignore swapped models.
        """
        operation = migrations.AddIndex('Pony', models.Index(fields=['pink'], name='my_name_idx'))
        project_state, new_state = self.make_test_state('test_adinigsw', operation)
        with connection.schema_editor() as editor:
            # No database queries should be run for swapped models
            operation.database_forwards('test_adinigsw', editor, project_state, new_state)
            operation.database_backwards('test_adinigsw', editor, new_state, project_state)

        operation = migrations.RemoveIndex('Pony', models.Index(fields=['pink'], name='my_name_idx'))
        project_state, new_state = self.make_test_state("test_rminigsw", operation)
        with connection.schema_editor() as editor:
            operation.database_forwards('test_rminigsw', editor, project_state, new_state)
            operation.database_backwards('test_rminigsw', editor, new_state, project_state)


class TestCreateModel(SimpleTestCase):

    def test_references_model_mixin(self):
        CreateModel('name', [], bases=(Mixin, models.Model)).references_model('other_model')
