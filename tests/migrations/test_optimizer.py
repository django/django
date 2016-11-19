from django.db import migrations, models
from django.db.migrations import operations
from django.db.migrations.optimizer import MigrationOptimizer
from django.test import SimpleTestCase

from .models import EmptyManager, UnicodeModel


class OptimizerTests(SimpleTestCase):
    """
    Tests the migration autodetector.
    """

    def optimize(self, operations, app_label):
        """
        Handy shortcut for getting results + number of loops
        """
        optimizer = MigrationOptimizer()
        return optimizer.optimize(operations, app_label), optimizer._iterations

    def assertOptimizesTo(self, operations, expected, exact=None, less_than=None, app_label=None):
        result, iterations = self.optimize(operations, app_label)
        result = [repr(f.deconstruct()) for f in result]
        expected = [repr(f.deconstruct()) for f in expected]
        self.assertEqual(expected, result)
        if exact is not None and iterations != exact:
            raise self.failureException(
                "Optimization did not take exactly %s iterations (it took %s)" % (exact, iterations)
            )
        if less_than is not None and iterations >= less_than:
            raise self.failureException(
                "Optimization did not take less than %s iterations (it took %s)" % (less_than, iterations)
            )

    def assertDoesNotOptimize(self, operations, **kwargs):
        self.assertOptimizesTo(operations, operations, **kwargs)

    def test_single(self):
        """
        The optimizer does nothing on a single operation,
        and that it does it in just one pass.
        """
        self.assertOptimizesTo(
            [migrations.DeleteModel("Foo")],
            [migrations.DeleteModel("Foo")],
            exact=1,
        )

    def test_create_delete_model(self):
        """
        CreateModel and DeleteModel should collapse into nothing.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.DeleteModel("Foo"),
            ],
            [],
        )

    def test_create_rename_model(self):
        """
        CreateModel should absorb RenameModels.
        """
        managers = [('objects', EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
                migrations.RenameModel("Foo", "Bar"),
            ],
            [
                migrations.CreateModel(
                    "Bar",
                    [("name", models.CharField(max_length=255))],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                )
            ],
        )

    def test_rename_model_self(self):
        """
        RenameModels should absorb themselves.
        """
        self.assertOptimizesTo(
            [
                migrations.RenameModel("Foo", "Baa"),
                migrations.RenameModel("Baa", "Bar"),
            ],
            [
                migrations.RenameModel("Foo", "Bar"),
            ],
        )

    def test_create_alter_model_options(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel('Foo', fields=[]),
                migrations.AlterModelOptions(name='Foo', options={'verbose_name_plural': 'Foozes'}),
            ],
            [
                migrations.CreateModel('Foo', fields=[], options={'verbose_name_plural': 'Foozes'}),
            ]
        )

    def _test_create_alter_foo_delete_model(self, alter_foo):
        """
        CreateModel, AlterModelTable, AlterUniqueTogether/AlterIndexTogether/
        AlterOrderWithRespectTo, and DeleteModel should collapse into nothing.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.AlterModelTable("Foo", "woohoo"),
                alter_foo,
                migrations.DeleteModel("Foo"),
            ],
            [],
        )

    def test_create_alter_unique_delete_model(self):
        self._test_create_alter_foo_delete_model(migrations.AlterUniqueTogether("Foo", [["a", "b"]]))

    def test_create_alter_index_delete_model(self):
        self._test_create_alter_foo_delete_model(migrations.AlterIndexTogether("Foo", [["a", "b"]]))

    def test_create_alter_owrt_delete_model(self):
        self._test_create_alter_foo_delete_model(migrations.AlterOrderWithRespectTo("Foo", "a"))

    def _test_alter_alter_model(self, alter_foo, alter_bar):
        """
        Two AlterUniqueTogether/AlterIndexTogether/AlterOrderWithRespectTo
        should collapse into the second.
        """
        self.assertOptimizesTo(
            [
                alter_foo,
                alter_bar,
            ],
            [
                alter_bar,
            ],
        )

    def test_alter_alter_table_model(self):
        self._test_alter_alter_model(
            migrations.AlterModelTable("Foo", "a"),
            migrations.AlterModelTable("Foo", "b"),
        )

    def test_alter_alter_unique_model(self):
        self._test_alter_alter_model(
            migrations.AlterUniqueTogether("Foo", [["a", "b"]]),
            migrations.AlterUniqueTogether("Foo", [["a", "c"]]),
        )

    def test_alter_alter_index_model(self):
        self._test_alter_alter_model(
            migrations.AlterIndexTogether("Foo", [["a", "b"]]),
            migrations.AlterIndexTogether("Foo", [["a", "c"]]),
        )

    def test_alter_alter_owrt_model(self):
        self._test_alter_alter_model(
            migrations.AlterOrderWithRespectTo("Foo", "a"),
            migrations.AlterOrderWithRespectTo("Foo", "b"),
        )

    def test_optimize_through_create(self):
        """
        We should be able to optimize away create/delete through a create or delete
        of a different model, but only if the create operation does not mention the model
        at all.
        """
        # These should work
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
            ],
        )
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.DeleteModel("Bar"),
                migrations.DeleteModel("Foo"),
            ],
            [],
        )
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.DeleteModel("Foo"),
                migrations.DeleteModel("Bar"),
            ],
            [],
        )
        # This should not work - FK should block it
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]),
                migrations.DeleteModel("Foo"),
            ],
        )
        # The same operations should be optimized if app_label is specified and
        # a FK references a model from the other app.
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel("Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]),
            ],
            app_label="otherapp",
        )
        # But it shouldn't work if a FK references a model with the same
        # app_label.
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]),
                migrations.DeleteModel("Foo"),
            ],
            app_label="testapp",
        )
        # This should not work - bases should block it
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())], bases=("testapp.Foo", )),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())], bases=("testapp.Foo", )),
                migrations.DeleteModel("Foo"),
            ],
        )
        # The same operations should be optimized if app_label and none of
        # bases belong to that app.
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())], bases=("testapp.Foo", )),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel("Bar", [("size", models.IntegerField())], bases=("testapp.Foo", )),
            ],
            app_label="otherapp",
        )
        # But it shouldn't work if some of bases belongs to the specified app.
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())], bases=("testapp.Foo", )),
                migrations.DeleteModel("Foo"),
            ],
            app_label="testapp",
        )

    def test_create_model_add_field(self):
        """
        AddField should optimize into CreateModel.
        """
        managers = [('objects', EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
                migrations.AddField("Foo", "age", models.IntegerField()),
            ],
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[
                        ("name", models.CharField(max_length=255)),
                        ("age", models.IntegerField()),
                    ],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
            ],
        )

    def test_create_model_add_field_not_through_fk(self):
        """
        AddField should NOT optimize into CreateModel if it's an FK to a model
        that's between them.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Link", [("url", models.TextField())]),
                migrations.AddField("Foo", "link", models.ForeignKey("migrations.Link", models.CASCADE)),
            ],
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Link", [("url", models.TextField())]),
                migrations.AddField("Foo", "link", models.ForeignKey("migrations.Link", models.CASCADE)),
            ],
        )

    def test_create_model_add_field_not_through_m2m_through(self):
        """
        AddField should NOT optimize into CreateModel if it's an M2M using a
        through that's created between them.
        """
        # Note: The middle model is not actually a valid through model,
        # but that doesn't matter, as we never render it.
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("LinkThrough", []),
                migrations.AddField(
                    "Foo", "link", models.ManyToManyField("migrations.Link", through="migrations.LinkThrough")
                ),
            ],
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("LinkThrough", []),
                migrations.AddField(
                    "Foo", "link", models.ManyToManyField("migrations.Link", through="migrations.LinkThrough")
                ),
            ],
        )

    def test_create_model_alter_field(self):
        """
        AlterField should optimize into CreateModel.
        """
        managers = [('objects', EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
                migrations.AlterField("Foo", "name", models.IntegerField()),
            ],
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[
                        ("name", models.IntegerField()),
                    ],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
            ],
        )

    def test_create_model_rename_field(self):
        """
        RenameField should optimize into CreateModel.
        """
        managers = [('objects', EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
                migrations.RenameField("Foo", "name", "title"),
            ],
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[
                        ("title", models.CharField(max_length=255)),
                    ],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
            ],
        )

    def test_add_field_rename_field(self):
        """
        RenameField should optimize into AddField
        """
        self.assertOptimizesTo(
            [
                migrations.AddField("Foo", "name", models.CharField(max_length=255)),
                migrations.RenameField("Foo", "name", "title"),
            ],
            [
                migrations.AddField("Foo", "title", models.CharField(max_length=255)),
            ],
        )

    def test_alter_field_rename_field(self):
        """
        RenameField should optimize to the other side of AlterField,
        and into itself.
        """
        self.assertOptimizesTo(
            [
                migrations.AlterField("Foo", "name", models.CharField(max_length=255)),
                migrations.RenameField("Foo", "name", "title"),
                migrations.RenameField("Foo", "title", "nom"),
            ],
            [
                migrations.RenameField("Foo", "name", "nom"),
                migrations.AlterField("Foo", "nom", models.CharField(max_length=255)),
            ],
        )

    def test_create_model_remove_field(self):
        """
        RemoveField should optimize into CreateModel.
        """
        managers = [('objects', EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[
                        ("name", models.CharField(max_length=255)),
                        ("age", models.IntegerField()),
                    ],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
                migrations.RemoveField("Foo", "age"),
            ],
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[
                        ("name", models.CharField(max_length=255)),
                    ],
                    options={'verbose_name': 'Foo'},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
            ],
        )

    def test_add_field_alter_field(self):
        """
        AlterField should optimize into AddField.
        """
        self.assertOptimizesTo(
            [
                migrations.AddField("Foo", "age", models.IntegerField()),
                migrations.AlterField("Foo", "age", models.FloatField(default=2.4)),
            ],
            [
                migrations.AddField("Foo", name="age", field=models.FloatField(default=2.4)),
            ],
        )

    def test_add_field_delete_field(self):
        """
        RemoveField should cancel AddField
        """
        self.assertOptimizesTo(
            [
                migrations.AddField("Foo", "age", models.IntegerField()),
                migrations.RemoveField("Foo", "age"),
            ],
            [],
        )

    def test_alter_field_delete_field(self):
        """
        RemoveField should absorb AlterField
        """
        self.assertOptimizesTo(
            [
                migrations.AlterField("Foo", "age", models.IntegerField()),
                migrations.RemoveField("Foo", "age"),
            ],
            [
                migrations.RemoveField("Foo", "age"),
            ],
        )

    def _test_create_alter_foo_field(self, alter):
        """
        CreateModel, AlterFooTogether/AlterOrderWithRespectTo followed by an
        add/alter/rename field should optimize to CreateModel and the Alter*
        """
        # AddField
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
                migrations.AddField("Foo", "c", models.IntegerField()),
            ],
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                    ("c", models.IntegerField()),
                ]),
                alter,
            ],
        )

        # AlterField
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
                migrations.AlterField("Foo", "b", models.CharField(max_length=255)),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                    ("c", models.IntegerField()),
                ]),
                alter,
                migrations.AlterField("Foo", "c", models.CharField(max_length=255)),
            ],
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                    ("c", models.CharField(max_length=255)),
                ]),
                alter,
            ],
        )

        # RenameField
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
                migrations.RenameField("Foo", "b", "c"),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
                migrations.RenameField("Foo", "b", "x"),
                migrations.RenameField("Foo", "x", "c"),
            ],
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
                migrations.RenameField("Foo", "b", "c"),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                    ("c", models.IntegerField()),
                ]),
                alter,
                migrations.RenameField("Foo", "c", "d"),
            ],
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                    ("d", models.IntegerField()),
                ]),
                alter,
            ],
        )

        # RemoveField
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
                migrations.RemoveField("Foo", "b"),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                    ("c", models.IntegerField()),
                ]),
                alter,
                migrations.RemoveField("Foo", "c"),
            ],
            [
                migrations.CreateModel("Foo", [
                    ("a", models.IntegerField()),
                    ("b", models.IntegerField()),
                ]),
                alter,
            ],
        )

    def test_create_alter_unique_field(self):
        self._test_create_alter_foo_field(migrations.AlterUniqueTogether("Foo", [["a", "b"]]))

    def test_create_alter_index_field(self):
        self._test_create_alter_foo_field(migrations.AlterIndexTogether("Foo", [["a", "b"]]))

    def test_create_alter_owrt_field(self):
        self._test_create_alter_foo_field(migrations.AlterOrderWithRespectTo("Foo", "b"))

    def test_optimize_through_fields(self):
        """
        field-level through checking is working. This should manage to collapse
        model Foo to nonexistence, and model Bar to a single IntegerField
        called "width".
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.AddField("Foo", "age", models.IntegerField()),
                migrations.AddField("Bar", "width", models.IntegerField()),
                migrations.AlterField("Foo", "age", models.IntegerField()),
                migrations.RenameField("Bar", "size", "dimensions"),
                migrations.RemoveField("Foo", "age"),
                migrations.RenameModel("Foo", "Phou"),
                migrations.RemoveField("Bar", "dimensions"),
                migrations.RenameModel("Phou", "Fou"),
                migrations.DeleteModel("Fou"),
            ],
            [
                migrations.CreateModel("Bar", [("width", models.IntegerField())]),
            ],
        )

    def test_optimize_elidable_operation(self):
        elidable_operation = operations.base.Operation()
        elidable_operation.elidable = True
        self.assertOptimizesTo(
            [
                elidable_operation,
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                elidable_operation,
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                elidable_operation,
                migrations.RenameModel("Foo", "Phou"),
                migrations.DeleteModel("Bar"),
                elidable_operation,
            ],
            [
                migrations.CreateModel("Phou", [("name", models.CharField(max_length=255))]),
            ],
        )
