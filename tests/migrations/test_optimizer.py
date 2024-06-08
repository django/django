from django.db import migrations, models
from django.db.migrations import operations
from django.db.migrations.optimizer import MigrationOptimizer
from django.db.migrations.serializer import serializer_factory
from django.db.models.functions import Abs
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

    def serialize(self, value):
        return serializer_factory(value).serialize()[0]

    def assertOptimizesTo(
        self, operations, expected, exact=None, less_than=None, app_label=None
    ):
        result, iterations = self.optimize(operations, app_label or "migrations")
        result = [self.serialize(f) for f in result]
        expected = [self.serialize(f) for f in expected]
        self.assertEqual(expected, result)
        if exact is not None and iterations != exact:
            raise self.failureException(
                "Optimization did not take exactly %s iterations (it took %s)"
                % (exact, iterations)
            )
        if less_than is not None and iterations >= less_than:
            raise self.failureException(
                "Optimization did not take less than %s iterations (it took %s)"
                % (less_than, iterations)
            )

    def assertDoesNotOptimize(self, operations, **kwargs):
        self.assertOptimizesTo(operations, operations, **kwargs)

    def test_none_app_label(self):
        optimizer = MigrationOptimizer()
        with self.assertRaisesMessage(TypeError, "app_label must be a str"):
            optimizer.optimize([], None)

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
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.DeleteModel("Foo"),
            ],
            [],
        )

    def test_create_rename_model(self):
        """
        CreateModel should absorb RenameModels.
        """
        managers = [("objects", EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={"verbose_name": "Foo"},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
                migrations.RenameModel("Foo", "Bar"),
            ],
            [
                migrations.CreateModel(
                    "Bar",
                    [("name", models.CharField(max_length=255))],
                    options={"verbose_name": "Foo"},
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
                migrations.CreateModel("Foo", fields=[]),
                migrations.AlterModelOptions(
                    name="Foo", options={"verbose_name_plural": "Foozes"}
                ),
            ],
            [
                migrations.CreateModel(
                    "Foo", fields=[], options={"verbose_name_plural": "Foozes"}
                ),
            ],
        )

    def test_create_alter_model_managers(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", fields=[]),
                migrations.AlterModelManagers(
                    name="Foo",
                    managers=[
                        ("objects", models.Manager()),
                        ("things", models.Manager()),
                    ],
                ),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    fields=[],
                    managers=[
                        ("objects", models.Manager()),
                        ("things", models.Manager()),
                    ],
                ),
            ],
        )

    def test_create_model_and_remove_model_options(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "MyModel",
                    fields=[],
                    options={"verbose_name": "My Model"},
                ),
                migrations.AlterModelOptions("MyModel", options={}),
            ],
            [migrations.CreateModel("MyModel", fields=[])],
        )
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "MyModel",
                    fields=[],
                    options={
                        "verbose_name": "My Model",
                        "verbose_name_plural": "My Model plural",
                    },
                ),
                migrations.AlterModelOptions(
                    "MyModel",
                    options={"verbose_name": "My Model"},
                ),
            ],
            [
                migrations.CreateModel(
                    "MyModel",
                    fields=[],
                    options={"verbose_name": "My Model"},
                ),
            ],
        )

    def _test_create_alter_foo_delete_model(self, alter_foo):
        """
        CreateModel, AlterModelTable, AlterUniqueTogether/AlterIndexTogether/
        AlterOrderWithRespectTo, and DeleteModel should collapse into nothing.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.AlterModelTable("Foo", "woohoo"),
                alter_foo,
                migrations.DeleteModel("Foo"),
            ],
            [],
        )

    def test_create_alter_unique_delete_model(self):
        self._test_create_alter_foo_delete_model(
            migrations.AlterUniqueTogether("Foo", [["a", "b"]])
        )

    def test_create_alter_index_delete_model(self):
        self._test_create_alter_foo_delete_model(
            migrations.AlterIndexTogether("Foo", [["a", "b"]])
        )

    def test_create_alter_owrt_delete_model(self):
        self._test_create_alter_foo_delete_model(
            migrations.AlterOrderWithRespectTo("Foo", "a")
        )

    def _test_alter_alter(self, alter_foo, alter_bar):
        """
        Two AlterUniqueTogether/AlterIndexTogether/AlterOrderWithRespectTo
        /AlterField should collapse into the second.
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
        self._test_alter_alter(
            migrations.AlterModelTable("Foo", "a"),
            migrations.AlterModelTable("Foo", "b"),
        )

    def test_alter_alter_unique_model(self):
        self._test_alter_alter(
            migrations.AlterUniqueTogether("Foo", [["a", "b"]]),
            migrations.AlterUniqueTogether("Foo", [["a", "c"]]),
        )

    def test_alter_alter_index_model(self):
        self._test_alter_alter(
            migrations.AlterIndexTogether("Foo", [["a", "b"]]),
            migrations.AlterIndexTogether("Foo", [["a", "c"]]),
        )

    def test_alter_alter_owrt_model(self):
        self._test_alter_alter(
            migrations.AlterOrderWithRespectTo("Foo", "a"),
            migrations.AlterOrderWithRespectTo("Foo", "b"),
        )

    def test_alter_alter_field(self):
        self._test_alter_alter(
            migrations.AlterField("Foo", "name", models.IntegerField()),
            migrations.AlterField("Foo", "name", models.IntegerField(help_text="help")),
        )

    def test_optimize_through_create(self):
        """
        We should be able to optimize away create/delete through a create or
        delete of a different model, but only if the create operation does not
        mention the model at all.
        """
        # These should work
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
            ],
        )
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.DeleteModel("Bar"),
                migrations.DeleteModel("Foo"),
            ],
            [],
        )
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                migrations.DeleteModel("Foo"),
                migrations.DeleteModel("Bar"),
            ],
            [],
        )
        # Operations should be optimized if the FK references a model from the
        # other app.
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]
                ),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel(
                    "Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]
                ),
            ],
            app_label="otherapp",
        )
        # But it shouldn't work if a FK references a model with the same
        # app_label.
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("other", models.ForeignKey("Foo", models.CASCADE))]
                ),
                migrations.DeleteModel("Foo"),
            ],
        )
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("other", models.ForeignKey("testapp.Foo", models.CASCADE))]
                ),
                migrations.DeleteModel("Foo"),
            ],
            app_label="testapp",
        )
        # This should not work - bases should block it
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("size", models.IntegerField())], bases=("Foo",)
                ),
                migrations.DeleteModel("Foo"),
            ],
        )
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("size", models.IntegerField())], bases=("testapp.Foo",)
                ),
                migrations.DeleteModel("Foo"),
            ],
            app_label="testapp",
        )
        # The same operations should be optimized if app_label and none of
        # bases belong to that app.
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("size", models.IntegerField())], bases=("testapp.Foo",)
                ),
                migrations.DeleteModel("Foo"),
            ],
            [
                migrations.CreateModel(
                    "Bar", [("size", models.IntegerField())], bases=("testapp.Foo",)
                ),
            ],
            app_label="otherapp",
        )
        # But it shouldn't work if some of bases belongs to the specified app.
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar", [("size", models.IntegerField())], bases=("testapp.Foo",)
                ),
                migrations.DeleteModel("Foo"),
            ],
            app_label="testapp",
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Book", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Person", [("name", models.CharField(max_length=255))]
                ),
                migrations.AddField(
                    "book",
                    "author",
                    models.ForeignKey("test_app.Person", models.CASCADE),
                ),
                migrations.CreateModel(
                    "Review",
                    [("book", models.ForeignKey("test_app.Book", models.CASCADE))],
                ),
                migrations.CreateModel(
                    "Reviewer", [("name", models.CharField(max_length=255))]
                ),
                migrations.AddField(
                    "review",
                    "reviewer",
                    models.ForeignKey("test_app.Reviewer", models.CASCADE),
                ),
                migrations.RemoveField("book", "author"),
                migrations.DeleteModel("Person"),
            ],
            [
                migrations.CreateModel(
                    "Book", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Reviewer", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Review",
                    [
                        ("book", models.ForeignKey("test_app.Book", models.CASCADE)),
                        (
                            "reviewer",
                            models.ForeignKey("test_app.Reviewer", models.CASCADE),
                        ),
                    ],
                ),
            ],
            app_label="test_app",
        )

    def test_create_model_add_field(self):
        """
        AddField should optimize into CreateModel.
        """
        managers = [("objects", EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={"verbose_name": "Foo"},
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
                    options={"verbose_name": "Foo"},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
            ],
        )

    def test_create_model_reordering(self):
        """
        AddField optimizes into CreateModel if it's a FK to a model that's
        between them (and there's no FK in the other direction), by changing
        the order of the CreateModel operations.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel("Link", [("url", models.TextField())]),
                migrations.AddField(
                    "Foo", "link", models.ForeignKey("migrations.Link", models.CASCADE)
                ),
            ],
            [
                migrations.CreateModel("Link", [("url", models.TextField())]),
                migrations.CreateModel(
                    "Foo",
                    [
                        ("name", models.CharField(max_length=255)),
                        ("link", models.ForeignKey("migrations.Link", models.CASCADE)),
                    ],
                ),
            ],
        )

    def test_create_model_reordering_circular_fk(self):
        """
        CreateModel reordering behavior doesn't result in an infinite loop if
        there are FKs in both directions.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Bar", [("url", models.TextField())]),
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.AddField(
                    "Bar", "foo_fk", models.ForeignKey("migrations.Foo", models.CASCADE)
                ),
                migrations.AddField(
                    "Foo", "bar_fk", models.ForeignKey("migrations.Bar", models.CASCADE)
                ),
            ],
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "Bar",
                    [
                        ("url", models.TextField()),
                        ("foo_fk", models.ForeignKey("migrations.Foo", models.CASCADE)),
                    ],
                ),
                migrations.AddField(
                    "Foo", "bar_fk", models.ForeignKey("migrations.Bar", models.CASCADE)
                ),
            ],
        )

    def test_create_model_no_reordering_for_unrelated_fk(self):
        """
        CreateModel order remains unchanged if the later AddField operation
        isn't a FK between them.
        """
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                migrations.CreateModel("Link", [("url", models.TextField())]),
                migrations.AddField(
                    "Other",
                    "link",
                    models.ForeignKey("migrations.Link", models.CASCADE),
                ),
            ],
        )

    def test_create_model_no_reordering_of_inherited_model(self):
        """
        A CreateModel that inherits from another isn't reordered to avoid
        moving it earlier than its parent CreateModel operation.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Other", [("foo", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "ParentModel", [("bar", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "ChildModel",
                    [("baz", models.CharField(max_length=255))],
                    bases=("migrations.parentmodel",),
                ),
                migrations.AddField(
                    "Other",
                    "fk",
                    models.ForeignKey("migrations.ChildModel", models.CASCADE),
                ),
            ],
            [
                migrations.CreateModel(
                    "ParentModel", [("bar", models.CharField(max_length=255))]
                ),
                migrations.CreateModel(
                    "ChildModel",
                    [("baz", models.CharField(max_length=255))],
                    bases=("migrations.parentmodel",),
                ),
                migrations.CreateModel(
                    "Other",
                    [
                        ("foo", models.CharField(max_length=255)),
                        (
                            "fk",
                            models.ForeignKey("migrations.ChildModel", models.CASCADE),
                        ),
                    ],
                ),
            ],
        )

    def test_create_model_add_field_not_through_m2m_through(self):
        """
        AddField should NOT optimize into CreateModel if it's an M2M using a
        through that's created between them.
        """
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel("Employee", []),
                migrations.CreateModel("Employer", []),
                migrations.CreateModel(
                    "Employment",
                    [
                        (
                            "employee",
                            models.ForeignKey("migrations.Employee", models.CASCADE),
                        ),
                        (
                            "employment",
                            models.ForeignKey("migrations.Employer", models.CASCADE),
                        ),
                    ],
                ),
                migrations.AddField(
                    "Employer",
                    "employees",
                    models.ManyToManyField(
                        "migrations.Employee",
                        through="migrations.Employment",
                    ),
                ),
            ],
        )

    def test_create_model_alter_field(self):
        """
        AlterField should optimize into CreateModel.
        """
        managers = [("objects", EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={"verbose_name": "Foo"},
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
                    options={"verbose_name": "Foo"},
                    bases=(UnicodeModel,),
                    managers=managers,
                ),
            ],
        )

    def test_create_model_rename_field(self):
        """
        RenameField should optimize into CreateModel.
        """
        managers = [("objects", EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[("name", models.CharField(max_length=255))],
                    options={"verbose_name": "Foo"},
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
                    options={"verbose_name": "Foo"},
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

    def test_swapping_fields_names(self):
        self.assertDoesNotOptimize(
            [
                migrations.CreateModel(
                    "MyModel",
                    [
                        ("field_a", models.IntegerField()),
                        ("field_b", models.IntegerField()),
                    ],
                ),
                migrations.RunPython(migrations.RunPython.noop),
                migrations.RenameField("MyModel", "field_a", "field_c"),
                migrations.RenameField("MyModel", "field_b", "field_a"),
                migrations.RenameField("MyModel", "field_c", "field_b"),
            ],
        )

    def test_create_model_remove_field(self):
        """
        RemoveField should optimize into CreateModel.
        """
        managers = [("objects", EmptyManager())]
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Foo",
                    fields=[
                        ("name", models.CharField(max_length=255)),
                        ("age", models.IntegerField()),
                    ],
                    options={"verbose_name": "Foo"},
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
                    options={"verbose_name": "Foo"},
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
                migrations.AddField(
                    "Foo", name="age", field=models.FloatField(default=2.4)
                ),
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
        add/alter/rename field should optimize to CreateModel with options.
        """
        option_value = getattr(alter, alter.option_name)
        options = {alter.option_name: option_value}

        # AddField
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.AddField("Foo", "c", models.IntegerField()),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                        ("c", models.IntegerField()),
                    ],
                    options=options,
                ),
            ],
        )

        # AlterField
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.AlterField("Foo", "b", models.CharField(max_length=255)),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.CharField(max_length=255)),
                    ],
                    options=options,
                ),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                        ("c", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.AlterField("Foo", "c", models.CharField(max_length=255)),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                        ("c", models.CharField(max_length=255)),
                    ],
                    options=options,
                ),
            ],
        )

        # RenameField
        if isinstance(option_value, str):
            renamed_options = {alter.option_name: "c"}
        else:
            renamed_options = {
                alter.option_name: {
                    tuple("c" if value == "b" else value for value in item)
                    for item in option_value
                }
            }
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.RenameField("Foo", "b", "c"),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("c", models.IntegerField()),
                    ],
                    options=renamed_options,
                ),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.RenameField("Foo", "b", "x"),
                migrations.RenameField("Foo", "x", "c"),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("c", models.IntegerField()),
                    ],
                    options=renamed_options,
                ),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                        ("c", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.RenameField("Foo", "c", "d"),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                        ("d", models.IntegerField()),
                    ],
                    options=options,
                ),
            ],
        )

        # RemoveField
        if isinstance(option_value, str):
            removed_options = None
        else:
            removed_options = {
                alter.option_name: {
                    tuple(value for value in item if value != "b")
                    for item in option_value
                }
            }
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.RemoveField("Foo", "b"),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                    ],
                    options=removed_options,
                ),
            ],
        )

        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                        ("c", models.IntegerField()),
                    ],
                ),
                alter,
                migrations.RemoveField("Foo", "c"),
            ],
            [
                migrations.CreateModel(
                    "Foo",
                    [
                        ("a", models.IntegerField()),
                        ("b", models.IntegerField()),
                    ],
                    options=options,
                ),
            ],
        )

    def test_create_alter_unique_field(self):
        self._test_create_alter_foo_field(
            migrations.AlterUniqueTogether("Foo", [["a", "b"]])
        )

    def test_create_alter_index_field(self):
        self._test_create_alter_foo_field(
            migrations.AlterIndexTogether("Foo", [["a", "b"]])
        )

    def test_create_alter_owrt_field(self):
        self._test_create_alter_foo_field(
            migrations.AlterOrderWithRespectTo("Foo", "b")
        )

    def test_optimize_through_fields(self):
        """
        field-level through checking is working. This should manage to collapse
        model Foo to nonexistence, and model Bar to a single IntegerField
        called "width".
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
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
                migrations.CreateModel(
                    "Foo", [("name", models.CharField(max_length=255))]
                ),
                elidable_operation,
                migrations.CreateModel("Bar", [("size", models.IntegerField())]),
                elidable_operation,
                migrations.RenameModel("Foo", "Phou"),
                migrations.DeleteModel("Bar"),
                elidable_operation,
            ],
            [
                migrations.CreateModel(
                    "Phou", [("name", models.CharField(max_length=255))]
                ),
            ],
        )

    def test_rename_index(self):
        self.assertOptimizesTo(
            [
                migrations.RenameIndex(
                    "Pony", new_name="mid_name", old_fields=("weight", "pink")
                ),
                migrations.RenameIndex(
                    "Pony", new_name="new_name", old_name="mid_name"
                ),
            ],
            [
                migrations.RenameIndex(
                    "Pony", new_name="new_name", old_fields=("weight", "pink")
                ),
            ],
        )
        self.assertOptimizesTo(
            [
                migrations.RenameIndex(
                    "Pony", new_name="mid_name", old_name="old_name"
                ),
                migrations.RenameIndex(
                    "Pony", new_name="new_name", old_name="mid_name"
                ),
            ],
            [migrations.RenameIndex("Pony", new_name="new_name", old_name="old_name")],
        )
        self.assertDoesNotOptimize(
            [
                migrations.RenameIndex(
                    "Pony", new_name="mid_name", old_name="old_name"
                ),
                migrations.RenameIndex(
                    "Pony", new_name="new_name", old_fields=("weight", "pink")
                ),
            ]
        )

    def test_add_rename_index(self):
        tests = [
            models.Index(fields=["weight", "pink"], name="mid_name"),
            models.Index(Abs("weight"), name="mid_name"),
            models.Index(
                Abs("weight"), name="mid_name", condition=models.Q(weight__gt=0)
            ),
        ]
        for index in tests:
            with self.subTest(index=index):
                renamed_index = index.clone()
                renamed_index.name = "new_name"
                self.assertOptimizesTo(
                    [
                        migrations.AddIndex("Pony", index),
                        migrations.RenameIndex(
                            "Pony", new_name="new_name", old_name="mid_name"
                        ),
                    ],
                    [
                        migrations.AddIndex("Pony", renamed_index),
                    ],
                )
                self.assertDoesNotOptimize(
                    [
                        migrations.AddIndex("Pony", index),
                        migrations.RenameIndex(
                            "Pony", new_name="new_name", old_name="other_name"
                        ),
                    ],
                )

    def test_add_remove_index(self):
        self.assertOptimizesTo(
            [
                migrations.AddIndex(
                    "Pony",
                    models.Index(
                        fields=["weight", "pink"], name="idx_pony_weight_pink"
                    ),
                ),
                migrations.RemoveIndex("Pony", "idx_pony_weight_pink"),
            ],
            [],
        )

    def test_add_remove_constraint(self):
        gt_constraint = models.CheckConstraint(
            condition=models.Q(pink__gt=2), name="constraint_pony_pink_gt_2"
        )
        self.assertOptimizesTo(
            [
                migrations.AddConstraint("Pony", gt_constraint),
                migrations.RemoveConstraint("Pony", gt_constraint.name),
            ],
            [],
        )
        self.assertDoesNotOptimize(
            [
                migrations.AddConstraint("Pony", gt_constraint),
                migrations.RemoveConstraint("Pony", "other_name"),
            ],
        )

    def test_create_model_add_index(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                        ("age", models.IntegerField()),
                    ],
                    options={
                        "indexes": [models.Index(fields=["age"], name="idx_pony_age")],
                    },
                ),
                migrations.AddIndex(
                    "Pony",
                    models.Index(fields=["weight"], name="idx_pony_weight"),
                ),
            ],
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                        ("age", models.IntegerField()),
                    ],
                    options={
                        "indexes": [
                            models.Index(fields=["age"], name="idx_pony_age"),
                            models.Index(fields=["weight"], name="idx_pony_weight"),
                        ],
                    },
                ),
            ],
        )

    def test_create_model_remove_index(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                        ("age", models.IntegerField()),
                    ],
                    options={
                        "indexes": [
                            models.Index(fields=["age"], name="idx_pony_age"),
                            models.Index(fields=["weight"], name="idx_pony_weight"),
                        ],
                    },
                ),
                migrations.RemoveIndex("Pony", "idx_pony_age"),
            ],
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                        ("age", models.IntegerField()),
                    ],
                    options={
                        "indexes": [
                            models.Index(fields=["weight"], name="idx_pony_weight"),
                        ],
                    },
                ),
            ],
        )

    def test_create_model_rename_index_no_old_fields(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                        ("age", models.IntegerField()),
                    ],
                    options={
                        "indexes": [models.Index(fields=["age"], name="idx_pony_age")],
                    },
                ),
                migrations.RenameIndex(
                    "Pony", new_name="idx_pony_age_new", old_name="idx_pony_age"
                ),
            ],
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                        ("age", models.IntegerField()),
                    ],
                    options={
                        "indexes": [models.Index(fields=["age"], name="idx_pony_age")],
                    },
                ),
                migrations.RenameIndex(
                    "Pony", new_name="idx_pony_age_new", old_name="idx_pony_age"
                ),
            ],
        )

    def test_create_model_add_constraint(self):
        gt_constraint = models.CheckConstraint(
            condition=models.Q(weight__gt=0), name="pony_weight_gt_0"
        )
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                    ],
                ),
                migrations.AddConstraint("Pony", gt_constraint),
            ],
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                    ],
                    options={"constraints": [gt_constraint]},
                ),
            ],
        )

    def test_create_model_remove_constraint(self):
        self.assertOptimizesTo(
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                    ],
                    options={
                        "constraints": [
                            models.CheckConstraint(
                                condition=models.Q(weight__gt=0),
                                name="pony_weight_gt_0",
                            ),
                            models.UniqueConstraint(
                                "weight", name="pony_weight_unique"
                            ),
                        ],
                    },
                ),
                migrations.RemoveConstraint("Pony", "pony_weight_gt_0"),
            ],
            [
                migrations.CreateModel(
                    name="Pony",
                    fields=[
                        ("weight", models.IntegerField()),
                    ],
                    options={
                        "constraints": [
                            models.UniqueConstraint(
                                "weight", name="pony_weight_unique"
                            ),
                        ]
                    },
                ),
            ],
        )
