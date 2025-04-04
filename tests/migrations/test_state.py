from django.apps.registry import Apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.db.migrations.exceptions import InvalidBasesError
from django.db.migrations.operations import (
    AddField,
    AlterField,
    DeleteModel,
    RemoveField,
)
from django.db.migrations.state import (
    ModelState,
    ProjectState,
    get_related_models_recursive,
)
from django.test import SimpleTestCase, override_settings
from django.test.utils import isolate_apps

from .models import (
    FoodManager,
    FoodQuerySet,
    ModelWithCustomBase,
    NoMigrationFoodManager,
    UnicodeModel,
)


class StateTests(SimpleTestCase):
    """
    Tests state construction, rendering and modification by operations.
    """

    def test_create(self):
        """
        Tests making a ProjectState from an Apps
        """

        new_apps = Apps(["migrations"])

        class Author(models.Model):
            name = models.CharField(max_length=255)
            bio = models.TextField()
            age = models.IntegerField(blank=True, null=True)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                unique_together = ["name", "bio"]

        class AuthorProxy(Author):
            class Meta:
                app_label = "migrations"
                apps = new_apps
                proxy = True
                ordering = ["name"]

        class SubAuthor(Author):
            width = models.FloatField(null=True)

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Book(models.Model):
            title = models.CharField(max_length=1000)
            author = models.ForeignKey(Author, models.CASCADE)
            contributors = models.ManyToManyField(Author)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                verbose_name = "tome"
                db_table = "test_tome"
                indexes = [models.Index(fields=["title"])]

        class Food(models.Model):
            food_mgr = FoodManager("a", "b")
            food_qs = FoodQuerySet.as_manager()
            food_no_mgr = NoMigrationFoodManager("x", "y")

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class FoodNoManagers(models.Model):
            class Meta:
                app_label = "migrations"
                apps = new_apps

        class FoodNoDefaultManager(models.Model):
            food_no_mgr = NoMigrationFoodManager("x", "y")
            food_mgr = FoodManager("a", "b")
            food_qs = FoodQuerySet.as_manager()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        mgr1 = FoodManager("a", "b")
        mgr2 = FoodManager("x", "y", c=3, d=4)

        class FoodOrderedManagers(models.Model):
            # The managers on this model should be ordered by their creation
            # counter and not by the order in model body

            food_no_mgr = NoMigrationFoodManager("x", "y")
            food_mgr2 = mgr2
            food_mgr1 = mgr1

            class Meta:
                app_label = "migrations"
                apps = new_apps

        project_state = ProjectState.from_apps(new_apps)
        author_state = project_state.models["migrations", "author"]
        author_proxy_state = project_state.models["migrations", "authorproxy"]
        sub_author_state = project_state.models["migrations", "subauthor"]
        book_state = project_state.models["migrations", "book"]
        food_state = project_state.models["migrations", "food"]
        food_no_managers_state = project_state.models["migrations", "foodnomanagers"]
        food_no_default_manager_state = project_state.models[
            "migrations", "foodnodefaultmanager"
        ]
        food_order_manager_state = project_state.models[
            "migrations", "foodorderedmanagers"
        ]
        book_index = models.Index(fields=["title"])
        book_index.set_name_with_model(Book)

        self.assertEqual(author_state.app_label, "migrations")
        self.assertEqual(author_state.name, "Author")
        self.assertEqual(list(author_state.fields), ["id", "name", "bio", "age"])
        self.assertEqual(author_state.fields["name"].max_length, 255)
        self.assertIs(author_state.fields["bio"].null, False)
        self.assertIs(author_state.fields["age"].null, True)
        self.assertEqual(
            author_state.options,
            {
                "unique_together": {("name", "bio")},
                "indexes": [],
                "constraints": [],
            },
        )
        self.assertEqual(author_state.bases, (models.Model,))

        self.assertEqual(book_state.app_label, "migrations")
        self.assertEqual(book_state.name, "Book")
        self.assertEqual(
            list(book_state.fields), ["id", "title", "author", "contributors"]
        )
        self.assertEqual(book_state.fields["title"].max_length, 1000)
        self.assertIs(book_state.fields["author"].null, False)
        self.assertEqual(
            book_state.fields["contributors"].__class__.__name__, "ManyToManyField"
        )
        self.assertEqual(
            book_state.options,
            {
                "verbose_name": "tome",
                "db_table": "test_tome",
                "indexes": [book_index],
                "constraints": [],
            },
        )
        self.assertEqual(book_state.bases, (models.Model,))

        self.assertEqual(author_proxy_state.app_label, "migrations")
        self.assertEqual(author_proxy_state.name, "AuthorProxy")
        self.assertEqual(author_proxy_state.fields, {})
        self.assertEqual(
            author_proxy_state.options,
            {"proxy": True, "ordering": ["name"], "indexes": [], "constraints": []},
        )
        self.assertEqual(author_proxy_state.bases, ("migrations.author",))

        self.assertEqual(sub_author_state.app_label, "migrations")
        self.assertEqual(sub_author_state.name, "SubAuthor")
        self.assertEqual(len(sub_author_state.fields), 2)
        self.assertEqual(sub_author_state.bases, ("migrations.author",))

        # The default manager is used in migrations
        self.assertEqual([name for name, mgr in food_state.managers], ["food_mgr"])
        self.assertTrue(all(isinstance(name, str) for name, mgr in food_state.managers))
        self.assertEqual(food_state.managers[0][1].args, ("a", "b", 1, 2))

        # No explicit managers defined. Migrations will fall back to the default
        self.assertEqual(food_no_managers_state.managers, [])

        # food_mgr is used in migration but isn't the default mgr, hence add the
        # default
        self.assertEqual(
            [name for name, mgr in food_no_default_manager_state.managers],
            ["food_no_mgr", "food_mgr"],
        )
        self.assertTrue(
            all(
                isinstance(name, str)
                for name, mgr in food_no_default_manager_state.managers
            )
        )
        self.assertEqual(
            food_no_default_manager_state.managers[0][1].__class__, models.Manager
        )
        self.assertIsInstance(food_no_default_manager_state.managers[1][1], FoodManager)

        self.assertEqual(
            [name for name, mgr in food_order_manager_state.managers],
            ["food_mgr1", "food_mgr2"],
        )
        self.assertTrue(
            all(
                isinstance(name, str) for name, mgr in food_order_manager_state.managers
            )
        )
        self.assertEqual(
            [mgr.args for name, mgr in food_order_manager_state.managers],
            [("a", "b", 1, 2), ("x", "y", 3, 4)],
        )

    def test_custom_default_manager_added_to_the_model_state(self):
        """
        When the default manager of the model is a custom manager,
        it needs to be added to the model state.
        """
        new_apps = Apps(["migrations"])
        custom_manager = models.Manager()

        class Author(models.Model):
            objects = models.TextField()
            authors = custom_manager

            class Meta:
                app_label = "migrations"
                apps = new_apps

        project_state = ProjectState.from_apps(new_apps)
        author_state = project_state.models["migrations", "author"]
        self.assertEqual(author_state.managers, [("authors", custom_manager)])

    def test_custom_default_manager_named_objects_with_false_migration_flag(self):
        """
        When a manager is added with a name of 'objects' but it does not
        have `use_in_migrations = True`, no migration should be added to the
        model state (#26643).
        """
        new_apps = Apps(["migrations"])

        class Author(models.Model):
            objects = models.Manager()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        project_state = ProjectState.from_apps(new_apps)
        author_state = project_state.models["migrations", "author"]
        self.assertEqual(author_state.managers, [])

    def test_no_duplicate_managers(self):
        """
        When a manager is added with `use_in_migrations = True` and a parent
        model had a manager with the same name and `use_in_migrations = True`,
        the parent's manager shouldn't appear in the model state (#26881).
        """
        new_apps = Apps(["migrations"])

        class PersonManager(models.Manager):
            use_in_migrations = True

        class Person(models.Model):
            objects = PersonManager()

            class Meta:
                abstract = True

        class BossManager(PersonManager):
            use_in_migrations = True

        class Boss(Person):
            objects = BossManager()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        project_state = ProjectState.from_apps(new_apps)
        boss_state = project_state.models["migrations", "boss"]
        self.assertEqual(boss_state.managers, [("objects", Boss.objects)])

    def test_custom_default_manager(self):
        new_apps = Apps(["migrations"])

        class Author(models.Model):
            manager1 = models.Manager()
            manager2 = models.Manager()

            class Meta:
                app_label = "migrations"
                apps = new_apps
                default_manager_name = "manager2"

        project_state = ProjectState.from_apps(new_apps)
        author_state = project_state.models["migrations", "author"]
        self.assertEqual(author_state.options["default_manager_name"], "manager2")
        self.assertEqual(author_state.managers, [("manager2", Author.manager1)])

    def test_custom_base_manager(self):
        new_apps = Apps(["migrations"])

        class Author(models.Model):
            manager1 = models.Manager()
            manager2 = models.Manager()

            class Meta:
                app_label = "migrations"
                apps = new_apps
                base_manager_name = "manager2"

        class Author2(models.Model):
            manager1 = models.Manager()
            manager2 = models.Manager()

            class Meta:
                app_label = "migrations"
                apps = new_apps
                base_manager_name = "manager1"

        project_state = ProjectState.from_apps(new_apps)

        author_state = project_state.models["migrations", "author"]
        self.assertEqual(author_state.options["base_manager_name"], "manager2")
        self.assertEqual(
            author_state.managers,
            [
                ("manager1", Author.manager1),
                ("manager2", Author.manager2),
            ],
        )

        author2_state = project_state.models["migrations", "author2"]
        self.assertEqual(author2_state.options["base_manager_name"], "manager1")
        self.assertEqual(
            author2_state.managers,
            [
                ("manager1", Author2.manager1),
            ],
        )

    def test_apps_bulk_update(self):
        """
        StateApps.bulk_update() should update apps.ready to False and reset
        the value afterward.
        """
        project_state = ProjectState()
        apps = project_state.apps
        with apps.bulk_update():
            self.assertFalse(apps.ready)
        self.assertTrue(apps.ready)
        with self.assertRaises(ValueError):
            with apps.bulk_update():
                self.assertFalse(apps.ready)
                raise ValueError()
        self.assertTrue(apps.ready)

    def test_render(self):
        """
        Tests rendering a ProjectState into an Apps.
        """
        project_state = ProjectState()
        project_state.add_model(
            ModelState(
                app_label="migrations",
                name="Tag",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("hidden", models.BooleanField()),
                ],
            )
        )
        project_state.add_model(
            ModelState(
                app_label="migrations",
                name="SubTag",
                fields=[
                    (
                        "tag_ptr",
                        models.OneToOneField(
                            "migrations.Tag",
                            models.CASCADE,
                            auto_created=True,
                            parent_link=True,
                            primary_key=True,
                            to_field="id",
                            serialize=False,
                        ),
                    ),
                    ("awesome", models.BooleanField()),
                ],
                bases=("migrations.Tag",),
            )
        )

        base_mgr = models.Manager()
        mgr1 = FoodManager("a", "b")
        mgr2 = FoodManager("x", "y", c=3, d=4)
        project_state.add_model(
            ModelState(
                app_label="migrations",
                name="Food",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                ],
                managers=[
                    # The ordering we really want is objects, mgr1, mgr2
                    ("default", base_mgr),
                    ("food_mgr2", mgr2),
                    ("food_mgr1", mgr1),
                ],
            )
        )

        new_apps = project_state.apps
        self.assertEqual(
            new_apps.get_model("migrations", "Tag")._meta.get_field("name").max_length,
            100,
        )
        self.assertIs(
            new_apps.get_model("migrations", "Tag")._meta.get_field("hidden").null,
            False,
        )

        self.assertEqual(
            len(new_apps.get_model("migrations", "SubTag")._meta.local_fields), 2
        )

        Food = new_apps.get_model("migrations", "Food")
        self.assertEqual(
            [mgr.name for mgr in Food._meta.managers],
            ["default", "food_mgr1", "food_mgr2"],
        )
        self.assertTrue(all(isinstance(mgr.name, str) for mgr in Food._meta.managers))
        self.assertEqual(
            [mgr.__class__ for mgr in Food._meta.managers],
            [models.Manager, FoodManager, FoodManager],
        )

    def test_render_model_inheritance(self):
        class Book(models.Model):
            title = models.CharField(max_length=1000)

            class Meta:
                app_label = "migrations"
                apps = Apps()

        class Novel(Book):
            class Meta:
                app_label = "migrations"
                apps = Apps()

        # First, test rendering individually
        apps = Apps(["migrations"])

        # We shouldn't be able to render yet
        ms = ModelState.from_model(Novel)
        with self.assertRaises(InvalidBasesError):
            ms.render(apps)

        # Once the parent model is in the app registry, it should be fine
        ModelState.from_model(Book).render(apps)
        ModelState.from_model(Novel).render(apps)

    def test_render_model_with_multiple_inheritance(self):
        class Foo(models.Model):
            class Meta:
                app_label = "migrations"
                apps = Apps()

        class Bar(models.Model):
            class Meta:
                app_label = "migrations"
                apps = Apps()

        class FooBar(Foo, Bar):
            class Meta:
                app_label = "migrations"
                apps = Apps()

        class AbstractSubFooBar(FooBar):
            class Meta:
                abstract = True
                apps = Apps()

        class SubFooBar(AbstractSubFooBar):
            class Meta:
                app_label = "migrations"
                apps = Apps()

        apps = Apps(["migrations"])

        # We shouldn't be able to render yet
        ms = ModelState.from_model(FooBar)
        with self.assertRaises(InvalidBasesError):
            ms.render(apps)

        # Once the parent models are in the app registry, it should be fine
        ModelState.from_model(Foo).render(apps)
        self.assertSequenceEqual(ModelState.from_model(Foo).bases, [models.Model])
        ModelState.from_model(Bar).render(apps)
        self.assertSequenceEqual(ModelState.from_model(Bar).bases, [models.Model])
        ModelState.from_model(FooBar).render(apps)
        self.assertSequenceEqual(
            ModelState.from_model(FooBar).bases, ["migrations.foo", "migrations.bar"]
        )
        ModelState.from_model(SubFooBar).render(apps)
        self.assertSequenceEqual(
            ModelState.from_model(SubFooBar).bases, ["migrations.foobar"]
        )

    def test_render_project_dependencies(self):
        """
        The ProjectState render method correctly renders models
        to account for inter-model base dependencies.
        """
        new_apps = Apps()

        class A(models.Model):
            class Meta:
                app_label = "migrations"
                apps = new_apps

        class B(A):
            class Meta:
                app_label = "migrations"
                apps = new_apps

        class C(B):
            class Meta:
                app_label = "migrations"
                apps = new_apps

        class D(A):
            class Meta:
                app_label = "migrations"
                apps = new_apps

        class E(B):
            class Meta:
                app_label = "migrations"
                apps = new_apps
                proxy = True

        class F(D):
            class Meta:
                app_label = "migrations"
                apps = new_apps
                proxy = True

        # Make a ProjectState and render it
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        project_state.add_model(ModelState.from_model(B))
        project_state.add_model(ModelState.from_model(C))
        project_state.add_model(ModelState.from_model(D))
        project_state.add_model(ModelState.from_model(E))
        project_state.add_model(ModelState.from_model(F))
        final_apps = project_state.apps
        self.assertEqual(len(final_apps.get_models()), 6)

        # Now make an invalid ProjectState and make sure it fails
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        project_state.add_model(ModelState.from_model(B))
        project_state.add_model(ModelState.from_model(C))
        project_state.add_model(ModelState.from_model(F))
        with self.assertRaises(InvalidBasesError):
            project_state.apps

    def test_render_unique_app_labels(self):
        """
        The ProjectState render method doesn't raise an
        ImproperlyConfigured exception about unique labels if two dotted app
        names have the same last part.
        """

        class A(models.Model):
            class Meta:
                app_label = "django.contrib.auth"

        class B(models.Model):
            class Meta:
                app_label = "vendor.auth"

        # Make a ProjectState and render it
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        project_state.add_model(ModelState.from_model(B))
        self.assertEqual(len(project_state.apps.get_models()), 2)

    def test_reload_related_model_on_non_relational_fields(self):
        """
        The model is reloaded even on changes that are not involved in
        relations. Other models pointing to or from it are also reloaded.
        """
        project_state = ProjectState()
        project_state.apps  # Render project state.
        project_state.add_model(ModelState("migrations", "A", []))
        project_state.add_model(
            ModelState(
                "migrations",
                "B",
                [
                    ("a", models.ForeignKey("A", models.CASCADE)),
                ],
            )
        )
        project_state.add_model(
            ModelState(
                "migrations",
                "C",
                [
                    ("b", models.ForeignKey("B", models.CASCADE)),
                    ("name", models.TextField()),
                ],
            )
        )
        project_state.add_model(
            ModelState(
                "migrations",
                "D",
                [
                    ("a", models.ForeignKey("A", models.CASCADE)),
                ],
            )
        )
        operation = AlterField(
            model_name="C",
            name="name",
            field=models.TextField(blank=True),
        )
        operation.state_forwards("migrations", project_state)
        project_state.reload_model("migrations", "a", delay=True)
        A = project_state.apps.get_model("migrations.A")
        B = project_state.apps.get_model("migrations.B")
        D = project_state.apps.get_model("migrations.D")
        self.assertIs(B._meta.get_field("a").related_model, A)
        self.assertIs(D._meta.get_field("a").related_model, A)

    def test_reload_model_relationship_consistency(self):
        project_state = ProjectState()
        project_state.add_model(ModelState("migrations", "A", []))
        project_state.add_model(
            ModelState(
                "migrations",
                "B",
                [
                    ("a", models.ForeignKey("A", models.CASCADE)),
                ],
            )
        )
        project_state.add_model(
            ModelState(
                "migrations",
                "C",
                [
                    ("b", models.ForeignKey("B", models.CASCADE)),
                ],
            )
        )
        A = project_state.apps.get_model("migrations.A")
        B = project_state.apps.get_model("migrations.B")
        C = project_state.apps.get_model("migrations.C")
        self.assertEqual([r.related_model for r in A._meta.related_objects], [B])
        self.assertEqual([r.related_model for r in B._meta.related_objects], [C])
        self.assertEqual([r.related_model for r in C._meta.related_objects], [])

        project_state.reload_model("migrations", "a", delay=True)
        A = project_state.apps.get_model("migrations.A")
        B = project_state.apps.get_model("migrations.B")
        C = project_state.apps.get_model("migrations.C")
        self.assertEqual([r.related_model for r in A._meta.related_objects], [B])
        self.assertEqual([r.related_model for r in B._meta.related_objects], [C])
        self.assertEqual([r.related_model for r in C._meta.related_objects], [])

    def test_add_relations(self):
        """
        #24573 - Adding relations to existing models should reload the
        referenced models too.
        """
        new_apps = Apps()

        class A(models.Model):
            class Meta:
                app_label = "something"
                apps = new_apps

        class B(A):
            class Meta:
                app_label = "something"
                apps = new_apps

        class C(models.Model):
            class Meta:
                app_label = "something"
                apps = new_apps

        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        project_state.add_model(ModelState.from_model(B))
        project_state.add_model(ModelState.from_model(C))

        project_state.apps  # We need to work with rendered models

        old_state = project_state.clone()
        model_a_old = old_state.apps.get_model("something", "A")
        model_b_old = old_state.apps.get_model("something", "B")
        model_c_old = old_state.apps.get_model("something", "C")
        # The relations between the old models are correct
        self.assertIs(model_a_old._meta.get_field("b").related_model, model_b_old)
        self.assertIs(model_b_old._meta.get_field("a_ptr").related_model, model_a_old)

        operation = AddField(
            "c",
            "to_a",
            models.OneToOneField(
                "something.A",
                models.CASCADE,
                related_name="from_c",
            ),
        )
        operation.state_forwards("something", project_state)
        model_a_new = project_state.apps.get_model("something", "A")
        model_b_new = project_state.apps.get_model("something", "B")
        model_c_new = project_state.apps.get_model("something", "C")

        # All models have changed
        self.assertIsNot(model_a_old, model_a_new)
        self.assertIsNot(model_b_old, model_b_new)
        self.assertIsNot(model_c_old, model_c_new)
        # The relations between the old models still hold
        self.assertIs(model_a_old._meta.get_field("b").related_model, model_b_old)
        self.assertIs(model_b_old._meta.get_field("a_ptr").related_model, model_a_old)
        # The relations between the new models correct
        self.assertIs(model_a_new._meta.get_field("b").related_model, model_b_new)
        self.assertIs(model_b_new._meta.get_field("a_ptr").related_model, model_a_new)
        self.assertIs(model_a_new._meta.get_field("from_c").related_model, model_c_new)
        self.assertIs(model_c_new._meta.get_field("to_a").related_model, model_a_new)

    def test_remove_relations(self):
        """
        #24225 - Relations between models are updated while
        remaining the relations and references for models of an old state.
        """
        new_apps = Apps()

        class A(models.Model):
            class Meta:
                app_label = "something"
                apps = new_apps

        class B(models.Model):
            to_a = models.ForeignKey(A, models.CASCADE)

            class Meta:
                app_label = "something"
                apps = new_apps

        def get_model_a(state):
            return [
                mod for mod in state.apps.get_models() if mod._meta.model_name == "a"
            ][0]

        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        project_state.add_model(ModelState.from_model(B))
        self.assertEqual(len(get_model_a(project_state)._meta.related_objects), 1)
        old_state = project_state.clone()

        operation = RemoveField("b", "to_a")
        operation.state_forwards("something", project_state)
        # Model from old_state still has the relation
        model_a_old = get_model_a(old_state)
        model_a_new = get_model_a(project_state)
        self.assertIsNot(model_a_old, model_a_new)
        self.assertEqual(len(model_a_old._meta.related_objects), 1)
        self.assertEqual(len(model_a_new._meta.related_objects), 0)

        # Same test for deleted model
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        project_state.add_model(ModelState.from_model(B))
        old_state = project_state.clone()

        operation = DeleteModel("b")
        operation.state_forwards("something", project_state)
        model_a_old = get_model_a(old_state)
        model_a_new = get_model_a(project_state)
        self.assertIsNot(model_a_old, model_a_new)
        self.assertEqual(len(model_a_old._meta.related_objects), 1)
        self.assertEqual(len(model_a_new._meta.related_objects), 0)

    def test_self_relation(self):
        """
        #24513 - Modifying an object pointing to itself would cause it to be
        rendered twice and thus breaking its related M2M through objects.
        """

        class A(models.Model):
            to_a = models.ManyToManyField("something.A", symmetrical=False)

            class Meta:
                app_label = "something"

        def get_model_a(state):
            return [
                mod for mod in state.apps.get_models() if mod._meta.model_name == "a"
            ][0]

        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(A))
        self.assertEqual(len(get_model_a(project_state)._meta.related_objects), 1)
        old_state = project_state.clone()

        operation = AlterField(
            model_name="a",
            name="to_a",
            field=models.ManyToManyField("something.A", symmetrical=False, blank=True),
        )
        # At this point the model would be rendered twice causing its related
        # M2M through objects to point to an old copy and thus breaking their
        # attribute lookup.
        operation.state_forwards("something", project_state)

        model_a_old = get_model_a(old_state)
        model_a_new = get_model_a(project_state)
        self.assertIsNot(model_a_old, model_a_new)

        # The old model's _meta is still consistent
        field_to_a_old = model_a_old._meta.get_field("to_a")
        self.assertEqual(field_to_a_old.m2m_field_name(), "from_a")
        self.assertEqual(field_to_a_old.m2m_reverse_field_name(), "to_a")
        self.assertIs(field_to_a_old.related_model, model_a_old)
        self.assertIs(
            field_to_a_old.remote_field.through._meta.get_field("to_a").related_model,
            model_a_old,
        )
        self.assertIs(
            field_to_a_old.remote_field.through._meta.get_field("from_a").related_model,
            model_a_old,
        )

        # The new model's _meta is still consistent
        field_to_a_new = model_a_new._meta.get_field("to_a")
        self.assertEqual(field_to_a_new.m2m_field_name(), "from_a")
        self.assertEqual(field_to_a_new.m2m_reverse_field_name(), "to_a")
        self.assertIs(field_to_a_new.related_model, model_a_new)
        self.assertIs(
            field_to_a_new.remote_field.through._meta.get_field("to_a").related_model,
            model_a_new,
        )
        self.assertIs(
            field_to_a_new.remote_field.through._meta.get_field("from_a").related_model,
            model_a_new,
        )

    def test_equality(self):
        """
        == and != are implemented correctly.
        """
        # Test two things that should be equal
        project_state = ProjectState()
        project_state.add_model(
            ModelState(
                "migrations",
                "Tag",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("hidden", models.BooleanField()),
                ],
                {},
                None,
            )
        )
        project_state.apps  # Fill the apps cached property
        other_state = project_state.clone()
        self.assertEqual(project_state, project_state)
        self.assertEqual(project_state, other_state)
        self.assertIs(project_state != project_state, False)
        self.assertIs(project_state != other_state, False)
        self.assertNotEqual(project_state.apps, other_state.apps)

        # Make a very small change (max_len 99) and see if that affects it
        project_state = ProjectState()
        project_state.add_model(
            ModelState(
                "migrations",
                "Tag",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=99)),
                    ("hidden", models.BooleanField()),
                ],
                {},
                None,
            )
        )
        self.assertNotEqual(project_state, other_state)
        self.assertIs(project_state == other_state, False)

    def test_dangling_references_throw_error(self):
        new_apps = Apps()

        class Author(models.Model):
            name = models.TextField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Publisher(models.Model):
            name = models.TextField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Book(models.Model):
            author = models.ForeignKey(Author, models.CASCADE)
            publisher = models.ForeignKey(Publisher, models.CASCADE)

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Magazine(models.Model):
            authors = models.ManyToManyField(Author)

            class Meta:
                app_label = "migrations"
                apps = new_apps

        # Make a valid ProjectState and render it
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(Author))
        project_state.add_model(ModelState.from_model(Publisher))
        project_state.add_model(ModelState.from_model(Book))
        project_state.add_model(ModelState.from_model(Magazine))
        self.assertEqual(len(project_state.apps.get_models()), 4)

        # now make an invalid one with a ForeignKey
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(Book))
        msg = (
            "The field migrations.Book.author was declared with a lazy reference "
            "to 'migrations.author', but app 'migrations' doesn't provide model "
            "'author'.\n"
            "The field migrations.Book.publisher was declared with a lazy reference "
            "to 'migrations.publisher', but app 'migrations' doesn't provide model "
            "'publisher'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            project_state.apps

        # And another with ManyToManyField.
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(Magazine))
        msg = (
            "The field migrations.Magazine.authors was declared with a lazy reference "
            "to 'migrations.author', but app 'migrations' doesn't provide model "
            "'author'.\n"
            "The field migrations.Magazine_authors.author was declared with a lazy "
            "reference to 'migrations.author', but app 'migrations' doesn't provide "
            "model 'author'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            project_state.apps

        # And now with multiple models and multiple fields.
        project_state.add_model(ModelState.from_model(Book))
        msg = (
            "The field migrations.Book.author was declared with a lazy reference "
            "to 'migrations.author', but app 'migrations' doesn't provide model "
            "'author'.\n"
            "The field migrations.Book.publisher was declared with a lazy reference "
            "to 'migrations.publisher', but app 'migrations' doesn't provide model "
            "'publisher'.\n"
            "The field migrations.Magazine.authors was declared with a lazy reference "
            "to 'migrations.author', but app 'migrations' doesn't provide model "
            "'author'.\n"
            "The field migrations.Magazine_authors.author was declared with a lazy "
            "reference to 'migrations.author', but app 'migrations' doesn't provide "
            "model 'author'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            project_state.apps

    def test_reference_mixed_case_app_label(self):
        new_apps = Apps()

        class Author(models.Model):
            class Meta:
                app_label = "MiXedCase_migrations"
                apps = new_apps

        class Book(models.Model):
            author = models.ForeignKey(Author, models.CASCADE)

            class Meta:
                app_label = "MiXedCase_migrations"
                apps = new_apps

        class Magazine(models.Model):
            authors = models.ManyToManyField(Author)

            class Meta:
                app_label = "MiXedCase_migrations"
                apps = new_apps

        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(Author))
        project_state.add_model(ModelState.from_model(Book))
        project_state.add_model(ModelState.from_model(Magazine))
        self.assertEqual(len(project_state.apps.get_models()), 3)

    def test_real_apps(self):
        """
        Including real apps can resolve dangling FK errors.
        This test relies on the fact that contenttypes is always loaded.
        """
        new_apps = Apps()

        class TestModel(models.Model):
            ct = models.ForeignKey("contenttypes.ContentType", models.CASCADE)

            class Meta:
                app_label = "migrations"
                apps = new_apps

        # If we just stick it into an empty state it should fail
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(TestModel))
        with self.assertRaises(ValueError):
            project_state.apps

        # If we include the real app it should succeed
        project_state = ProjectState(real_apps={"contenttypes"})
        project_state.add_model(ModelState.from_model(TestModel))
        rendered_state = project_state.apps
        self.assertEqual(
            len(
                [
                    x
                    for x in rendered_state.get_models()
                    if x._meta.app_label == "migrations"
                ]
            ),
            1,
        )

    def test_real_apps_non_set(self):
        with self.assertRaises(AssertionError):
            ProjectState(real_apps=["contenttypes"])

    def test_ignore_order_wrt(self):
        """
        Makes sure ProjectState doesn't include OrderWrt fields when
        making from existing models.
        """
        new_apps = Apps()

        class Author(models.Model):
            name = models.TextField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Book(models.Model):
            author = models.ForeignKey(Author, models.CASCADE)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                order_with_respect_to = "author"

        # Make a valid ProjectState and render it
        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(Author))
        project_state.add_model(ModelState.from_model(Book))
        self.assertEqual(
            list(project_state.models["migrations", "book"].fields),
            ["id", "author"],
        )

    def test_modelstate_get_field_order_wrt(self):
        new_apps = Apps()

        class Author(models.Model):
            name = models.TextField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Book(models.Model):
            author = models.ForeignKey(Author, models.CASCADE)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                order_with_respect_to = "author"

        model_state = ModelState.from_model(Book)
        order_wrt_field = model_state.get_field("_order")
        self.assertIsInstance(order_wrt_field, models.ForeignKey)
        self.assertEqual(order_wrt_field.related_model, "migrations.author")

    def test_modelstate_get_field_no_order_wrt_order_field(self):
        new_apps = Apps()

        class HistoricalRecord(models.Model):
            _order = models.PositiveSmallIntegerField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        model_state = ModelState.from_model(HistoricalRecord)
        order_field = model_state.get_field("_order")
        self.assertIsNone(order_field.related_model)
        self.assertIsInstance(order_field, models.PositiveSmallIntegerField)

    def test_get_order_field_after_removed_order_with_respect_to_field(self):
        new_apps = Apps()

        class HistoricalRecord(models.Model):
            _order = models.PositiveSmallIntegerField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        model_state = ModelState.from_model(HistoricalRecord)
        model_state.options["order_with_respect_to"] = None
        order_field = model_state.get_field("_order")
        self.assertIsNone(order_field.related_model)
        self.assertIsInstance(order_field, models.PositiveSmallIntegerField)

    def test_manager_refer_correct_model_version(self):
        """
        #24147 - Managers refer to the correct version of a
        historical model
        """
        project_state = ProjectState()
        project_state.add_model(
            ModelState(
                app_label="migrations",
                name="Tag",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("hidden", models.BooleanField()),
                ],
                managers=[
                    ("food_mgr", FoodManager("a", "b")),
                    ("food_qs", FoodQuerySet.as_manager()),
                ],
            )
        )

        old_model = project_state.apps.get_model("migrations", "tag")

        new_state = project_state.clone()
        operation = RemoveField("tag", "hidden")
        operation.state_forwards("migrations", new_state)

        new_model = new_state.apps.get_model("migrations", "tag")

        self.assertIsNot(old_model, new_model)
        self.assertIs(old_model, old_model.food_mgr.model)
        self.assertIs(old_model, old_model.food_qs.model)
        self.assertIs(new_model, new_model.food_mgr.model)
        self.assertIs(new_model, new_model.food_qs.model)
        self.assertIsNot(old_model.food_mgr, new_model.food_mgr)
        self.assertIsNot(old_model.food_qs, new_model.food_qs)
        self.assertIsNot(old_model.food_mgr.model, new_model.food_mgr.model)
        self.assertIsNot(old_model.food_qs.model, new_model.food_qs.model)

    def test_choices_iterator(self):
        """
        #24483 - ProjectState.from_apps should not destructively consume
        Field.choices iterators.
        """
        new_apps = Apps(["migrations"])
        choices = [("a", "A"), ("b", "B")]

        class Author(models.Model):
            name = models.CharField(max_length=255)
            choice = models.CharField(max_length=255, choices=iter(choices))

            class Meta:
                app_label = "migrations"
                apps = new_apps

        ProjectState.from_apps(new_apps)
        choices_field = Author._meta.get_field("choice")
        self.assertEqual(list(choices_field.choices), choices)

    def test_composite_pk_state(self):
        new_apps = Apps(["migrations"])

        class Foo(models.Model):
            pk = models.CompositePrimaryKey("account_id", "id")
            account_id = models.SmallIntegerField()
            id = models.SmallIntegerField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        project_state = ProjectState.from_apps(new_apps)
        model_state = project_state.models["migrations", "foo"]
        self.assertEqual(len(model_state.options), 2)
        self.assertEqual(model_state.options["constraints"], [])
        self.assertEqual(model_state.options["indexes"], [])
        self.assertEqual(len(model_state.fields), 3)
        self.assertIn("pk", model_state.fields)
        self.assertIn("account_id", model_state.fields)
        self.assertIn("id", model_state.fields)


class StateRelationsTests(SimpleTestCase):
    def get_base_project_state(self):
        new_apps = Apps()

        class User(models.Model):
            class Meta:
                app_label = "tests"
                apps = new_apps

        class Comment(models.Model):
            text = models.TextField()
            user = models.ForeignKey(User, models.CASCADE)
            comments = models.ManyToManyField("self")

            class Meta:
                app_label = "tests"
                apps = new_apps

        class Post(models.Model):
            text = models.TextField()
            authors = models.ManyToManyField(User)

            class Meta:
                app_label = "tests"
                apps = new_apps

        project_state = ProjectState()
        project_state.add_model(ModelState.from_model(User))
        project_state.add_model(ModelState.from_model(Comment))
        project_state.add_model(ModelState.from_model(Post))
        return project_state

    def test_relations_population(self):
        tests = [
            (
                "add_model",
                [
                    ModelState(
                        app_label="migrations",
                        name="Tag",
                        fields=[("id", models.AutoField(primary_key=True))],
                    ),
                ],
            ),
            ("remove_model", ["tests", "comment"]),
            ("rename_model", ["tests", "comment", "opinion"]),
            (
                "add_field",
                [
                    "tests",
                    "post",
                    "next_post",
                    models.ForeignKey("self", models.CASCADE),
                    True,
                ],
            ),
            ("remove_field", ["tests", "post", "text"]),
            ("rename_field", ["tests", "comment", "user", "author"]),
            (
                "alter_field",
                [
                    "tests",
                    "comment",
                    "user",
                    models.IntegerField(),
                    True,
                ],
            ),
        ]
        for method, args in tests:
            with self.subTest(method=method):
                project_state = self.get_base_project_state()
                getattr(project_state, method)(*args)
                # ProjectState's `_relations` are populated on `relations` access.
                self.assertIsNone(project_state._relations)
                self.assertEqual(project_state.relations, project_state._relations)
                self.assertIsNotNone(project_state._relations)

    def test_add_model(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        self.assertEqual(
            list(project_state.relations["tests", "comment"]),
            [("tests", "comment")],
        )
        self.assertNotIn(("tests", "post"), project_state.relations)

    def test_add_model_no_relations(self):
        project_state = ProjectState()
        project_state.add_model(
            ModelState(
                app_label="migrations",
                name="Tag",
                fields=[("id", models.AutoField(primary_key=True))],
            )
        )
        self.assertEqual(project_state.relations, {})

    def test_add_model_other_app(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        project_state.add_model(
            ModelState(
                app_label="tests_other",
                name="comment",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("user", models.ForeignKey("tests.user", models.CASCADE)),
                ],
            )
        )
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post"), ("tests_other", "comment")],
        )

    def test_remove_model(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        self.assertEqual(
            list(project_state.relations["tests", "comment"]),
            [("tests", "comment")],
        )

        project_state.remove_model("tests", "comment")
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "post")],
        )
        self.assertNotIn(("tests", "comment"), project_state.relations)
        project_state.remove_model("tests", "post")
        self.assertEqual(project_state.relations, {})
        project_state.remove_model("tests", "user")
        self.assertEqual(project_state.relations, {})

    def test_rename_model(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        self.assertEqual(
            list(project_state.relations["tests", "comment"]),
            [("tests", "comment")],
        )

        related_field = project_state.relations["tests", "user"]["tests", "comment"]
        project_state.rename_model("tests", "comment", "opinion")
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "post"), ("tests", "opinion")],
        )
        self.assertEqual(
            list(project_state.relations["tests", "opinion"]),
            [("tests", "opinion")],
        )
        self.assertNotIn(("tests", "comment"), project_state.relations)
        self.assertEqual(
            project_state.relations["tests", "user"]["tests", "opinion"],
            related_field,
        )

        project_state.rename_model("tests", "user", "author")
        self.assertEqual(
            list(project_state.relations["tests", "author"]),
            [("tests", "post"), ("tests", "opinion")],
        )
        self.assertNotIn(("tests", "user"), project_state.relations)

    def test_rename_model_no_relations(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        related_field = project_state.relations["tests", "user"]["tests", "post"]
        self.assertNotIn(("tests", "post"), project_state.relations)
        # Rename a model without relations.
        project_state.rename_model("tests", "post", "blog")
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "blog")],
        )
        self.assertNotIn(("tests", "blog"), project_state.relations)
        self.assertEqual(
            related_field,
            project_state.relations["tests", "user"]["tests", "blog"],
        )

    def test_add_field(self):
        project_state = self.get_base_project_state()
        self.assertNotIn(("tests", "post"), project_state.relations)
        # Add a self-referential foreign key.
        new_field = models.ForeignKey("self", models.CASCADE)
        project_state.add_field(
            "tests",
            "post",
            "next_post",
            new_field,
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "post"]),
            [("tests", "post")],
        )
        self.assertEqual(
            project_state.relations["tests", "post"]["tests", "post"],
            {"next_post": new_field},
        )
        # Add a foreign key.
        new_field = models.ForeignKey("tests.post", models.CASCADE)
        project_state.add_field(
            "tests",
            "comment",
            "post",
            new_field,
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "post"]),
            [("tests", "post"), ("tests", "comment")],
        )
        self.assertEqual(
            project_state.relations["tests", "post"]["tests", "comment"],
            {"post": new_field},
        )

    def test_add_field_m2m_with_through(self):
        project_state = self.get_base_project_state()
        project_state.add_model(
            ModelState(
                app_label="tests",
                name="Tag",
                fields=[("id", models.AutoField(primary_key=True))],
            )
        )
        project_state.add_model(
            ModelState(
                app_label="tests",
                name="PostTag",
                fields=[
                    ("id", models.AutoField(primary_key=True)),
                    ("post", models.ForeignKey("tests.post", models.CASCADE)),
                    ("tag", models.ForeignKey("tests.tag", models.CASCADE)),
                ],
            )
        )
        self.assertEqual(
            list(project_state.relations["tests", "post"]),
            [("tests", "posttag")],
        )
        self.assertEqual(
            list(project_state.relations["tests", "tag"]),
            [("tests", "posttag")],
        )
        # Add a many-to-many field with the through model.
        new_field = models.ManyToManyField("tests.tag", through="tests.posttag")
        project_state.add_field(
            "tests",
            "post",
            "tags",
            new_field,
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "post"]),
            [("tests", "posttag")],
        )
        self.assertEqual(
            list(project_state.relations["tests", "tag"]),
            [("tests", "posttag"), ("tests", "post")],
        )
        self.assertEqual(
            project_state.relations["tests", "tag"]["tests", "post"],
            {"tags": new_field},
        )

    def test_remove_field(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        # Remove a many-to-many field.
        project_state.remove_field("tests", "post", "authors")
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment")],
        )
        # Remove a foreign key.
        project_state.remove_field("tests", "comment", "user")
        self.assertEqual(project_state.relations["tests", "user"], {})

    def test_remove_field_no_relations(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        # Remove a non-relation field.
        project_state.remove_field("tests", "post", "text")
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )

    def test_rename_field(self):
        project_state = self.get_base_project_state()
        field = project_state.models["tests", "comment"].fields["user"]
        self.assertEqual(
            project_state.relations["tests", "user"]["tests", "comment"],
            {"user": field},
        )

        project_state.rename_field("tests", "comment", "user", "author")
        renamed_field = project_state.models["tests", "comment"].fields["author"]
        self.assertEqual(
            project_state.relations["tests", "user"]["tests", "comment"],
            {"author": renamed_field},
        )
        self.assertEqual(field, renamed_field)

    def test_rename_field_no_relations(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        # Rename a non-relation field.
        project_state.rename_field("tests", "post", "text", "description")
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )

    def test_alter_field(self):
        project_state = self.get_base_project_state()
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        # Alter a foreign key to a non-relation field.
        project_state.alter_field(
            "tests",
            "comment",
            "user",
            models.IntegerField(),
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "post")],
        )
        # Alter a non-relation field to a many-to-many field.
        m2m_field = models.ManyToManyField("tests.user")
        project_state.alter_field(
            "tests",
            "comment",
            "user",
            m2m_field,
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "post"), ("tests", "comment")],
        )
        self.assertEqual(
            project_state.relations["tests", "user"]["tests", "comment"],
            {"user": m2m_field},
        )

    def test_alter_field_m2m_to_fk(self):
        project_state = self.get_base_project_state()
        project_state.add_model(
            ModelState(
                app_label="tests_other",
                name="user_other",
                fields=[("id", models.AutoField(primary_key=True))],
            )
        )
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        self.assertNotIn(("tests_other", "user_other"), project_state.relations)
        # Alter a many-to-many field to a foreign key.
        foreign_key = models.ForeignKey("tests_other.user_other", models.CASCADE)
        project_state.alter_field(
            "tests",
            "post",
            "authors",
            foreign_key,
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment")],
        )
        self.assertEqual(
            list(project_state.relations["tests_other", "user_other"]),
            [("tests", "post")],
        )
        self.assertEqual(
            project_state.relations["tests_other", "user_other"]["tests", "post"],
            {"authors": foreign_key},
        )

    def test_many_relations_to_same_model(self):
        project_state = self.get_base_project_state()
        new_field = models.ForeignKey("tests.user", models.CASCADE)
        project_state.add_field(
            "tests",
            "comment",
            "reviewer",
            new_field,
            preserve_default=True,
        )
        self.assertEqual(
            list(project_state.relations["tests", "user"]),
            [("tests", "comment"), ("tests", "post")],
        )
        comment_rels = project_state.relations["tests", "user"]["tests", "comment"]
        # Two foreign keys to the same model.
        self.assertEqual(len(comment_rels), 2)
        self.assertEqual(comment_rels["reviewer"], new_field)
        # Rename the second foreign key.
        project_state.rename_field("tests", "comment", "reviewer", "supervisor")
        self.assertEqual(len(comment_rels), 2)
        self.assertEqual(comment_rels["supervisor"], new_field)
        # Remove the first foreign key.
        project_state.remove_field("tests", "comment", "user")
        self.assertEqual(comment_rels, {"supervisor": new_field})


class ModelStateTests(SimpleTestCase):
    def test_custom_model_base(self):
        state = ModelState.from_model(ModelWithCustomBase)
        self.assertEqual(state.bases, (models.Model,))

    def test_bound_field_sanity_check(self):
        field = models.CharField(max_length=1)
        field.model = models.Model
        with self.assertRaisesMessage(
            ValueError, 'ModelState.fields cannot be bound to a model - "field" is.'
        ):
            ModelState("app", "Model", [("field", field)])

    def test_sanity_check_to(self):
        field = models.ForeignKey(UnicodeModel, models.CASCADE)
        with self.assertRaisesMessage(
            ValueError,
            'Model fields in "ModelState.fields" cannot refer to a model class - '
            '"app.Model.field.to" does. Use a string reference instead.',
        ):
            ModelState("app", "Model", [("field", field)])

    def test_sanity_check_through(self):
        field = models.ManyToManyField("UnicodeModel")
        field.remote_field.through = UnicodeModel
        with self.assertRaisesMessage(
            ValueError,
            'Model fields in "ModelState.fields" cannot refer to a model class - '
            '"app.Model.field.through" does. Use a string reference instead.',
        ):
            ModelState("app", "Model", [("field", field)])

    def test_sanity_index_name(self):
        field = models.IntegerField()
        options = {"indexes": [models.Index(fields=["field"])]}
        msg = (
            "Indexes passed to ModelState require a name attribute. <Index: "
            "fields=['field']> doesn't have one."
        )
        with self.assertRaisesMessage(ValueError, msg):
            ModelState("app", "Model", [("field", field)], options=options)

    def test_fields_immutability(self):
        """
        Rendering a model state doesn't alter its internal fields.
        """
        apps = Apps()
        field = models.CharField(max_length=1)
        state = ModelState("app", "Model", [("name", field)])
        Model = state.render(apps)
        self.assertNotEqual(Model._meta.get_field("name"), field)

    def test_repr(self):
        field = models.CharField(max_length=1)
        state = ModelState(
            "app", "Model", [("name", field)], bases=["app.A", "app.B", "app.C"]
        )
        self.assertEqual(repr(state), "<ModelState: 'app.Model'>")

        project_state = ProjectState()
        project_state.add_model(state)
        with self.assertRaisesMessage(
            InvalidBasesError, "Cannot resolve bases for [<ModelState: 'app.Model'>]"
        ):
            project_state.apps

    def test_fields_ordering_equality(self):
        state = ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("hidden", models.BooleanField()),
            ],
        )
        reordered_state = ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                # Purposely re-ordered.
                ("hidden", models.BooleanField()),
                ("name", models.CharField(max_length=100)),
            ],
        )
        self.assertEqual(state, reordered_state)

    @override_settings(TEST_SWAPPABLE_MODEL="migrations.SomeFakeModel")
    def test_create_swappable(self):
        """
        Tests making a ProjectState from an Apps with a swappable model
        """
        new_apps = Apps(["migrations"])

        class Author(models.Model):
            name = models.CharField(max_length=255)
            bio = models.TextField()
            age = models.IntegerField(blank=True, null=True)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                swappable = "TEST_SWAPPABLE_MODEL"

        author_state = ModelState.from_model(Author)
        self.assertEqual(author_state.app_label, "migrations")
        self.assertEqual(author_state.name, "Author")
        self.assertEqual(list(author_state.fields), ["id", "name", "bio", "age"])
        self.assertEqual(author_state.fields["name"].max_length, 255)
        self.assertIs(author_state.fields["bio"].null, False)
        self.assertIs(author_state.fields["age"].null, True)
        self.assertEqual(
            author_state.options,
            {"swappable": "TEST_SWAPPABLE_MODEL", "indexes": [], "constraints": []},
        )
        self.assertEqual(author_state.bases, (models.Model,))
        self.assertEqual(author_state.managers, [])

    @override_settings(TEST_SWAPPABLE_MODEL="migrations.SomeFakeModel")
    def test_create_swappable_from_abstract(self):
        """
        A swappable model inheriting from a hierarchy:
        concrete -> abstract -> concrete.
        """
        new_apps = Apps(["migrations"])

        class SearchableLocation(models.Model):
            keywords = models.CharField(max_length=256)

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Station(SearchableLocation):
            name = models.CharField(max_length=128)

            class Meta:
                abstract = True

        class BusStation(Station):
            bus_routes = models.CharField(max_length=128)
            inbound = models.BooleanField(default=False)

            class Meta(Station.Meta):
                app_label = "migrations"
                apps = new_apps
                swappable = "TEST_SWAPPABLE_MODEL"

        station_state = ModelState.from_model(BusStation)
        self.assertEqual(station_state.app_label, "migrations")
        self.assertEqual(station_state.name, "BusStation")
        self.assertEqual(
            list(station_state.fields),
            ["searchablelocation_ptr", "name", "bus_routes", "inbound"],
        )
        self.assertEqual(station_state.fields["name"].max_length, 128)
        self.assertIs(station_state.fields["bus_routes"].null, False)
        self.assertEqual(
            station_state.options,
            {
                "abstract": False,
                "swappable": "TEST_SWAPPABLE_MODEL",
                "indexes": [],
                "constraints": [],
            },
        )
        self.assertEqual(station_state.bases, ("migrations.searchablelocation",))
        self.assertEqual(station_state.managers, [])

    @override_settings(TEST_SWAPPABLE_MODEL="migrations.SomeFakeModel")
    def test_custom_manager_swappable(self):
        """
        Tests making a ProjectState from unused models with custom managers
        """
        new_apps = Apps(["migrations"])

        class Food(models.Model):
            food_mgr = FoodManager("a", "b")
            food_qs = FoodQuerySet.as_manager()
            food_no_mgr = NoMigrationFoodManager("x", "y")

            class Meta:
                app_label = "migrations"
                apps = new_apps
                swappable = "TEST_SWAPPABLE_MODEL"

        food_state = ModelState.from_model(Food)

        # The default manager is used in migrations
        self.assertEqual([name for name, mgr in food_state.managers], ["food_mgr"])
        self.assertEqual(food_state.managers[0][1].args, ("a", "b", 1, 2))

    @isolate_apps("migrations", "django.contrib.contenttypes")
    def test_order_with_respect_to_private_field(self):
        class PrivateFieldModel(models.Model):
            content_type = models.ForeignKey("contenttypes.ContentType", models.CASCADE)
            object_id = models.PositiveIntegerField()
            private = GenericForeignKey()

            class Meta:
                order_with_respect_to = "private"

        state = ModelState.from_model(PrivateFieldModel)
        self.assertNotIn("order_with_respect_to", state.options)

    @isolate_apps("migrations")
    def test_abstract_model_children_inherit_indexes(self):
        class Abstract(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                app_label = "migrations"
                abstract = True
                indexes = [models.Index(fields=["name"])]

        class Child1(Abstract):
            pass

        class Child2(Abstract):
            pass

        abstract_state = ModelState.from_model(Abstract)
        child1_state = ModelState.from_model(Child1)
        child2_state = ModelState.from_model(Child2)
        index_names = [index.name for index in abstract_state.options["indexes"]]
        self.assertEqual(index_names, ["migrations__name_ae16a4_idx"])
        index_names = [index.name for index in child1_state.options["indexes"]]
        self.assertEqual(index_names, ["migrations__name_b0afd7_idx"])
        index_names = [index.name for index in child2_state.options["indexes"]]
        self.assertEqual(index_names, ["migrations__name_016466_idx"])

        # Modifying the state doesn't modify the index on the model.
        child1_state.options["indexes"][0].name = "bar"
        self.assertEqual(Child1._meta.indexes[0].name, "migrations__name_b0afd7_idx")

    @isolate_apps("migrations")
    def test_explicit_index_name(self):
        class TestModel(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                app_label = "migrations"
                indexes = [models.Index(fields=["name"], name="foo_idx")]

        model_state = ModelState.from_model(TestModel)
        index_names = [index.name for index in model_state.options["indexes"]]
        self.assertEqual(index_names, ["foo_idx"])

    @isolate_apps("migrations")
    def test_from_model_constraints(self):
        class ModelWithConstraints(models.Model):
            size = models.IntegerField()

            class Meta:
                constraints = [
                    models.CheckConstraint(
                        condition=models.Q(size__gt=1), name="size_gt_1"
                    )
                ]

        state = ModelState.from_model(ModelWithConstraints)
        model_constraints = ModelWithConstraints._meta.constraints
        state_constraints = state.options["constraints"]
        self.assertEqual(model_constraints, state_constraints)
        self.assertIsNot(model_constraints, state_constraints)
        self.assertIsNot(model_constraints[0], state_constraints[0])


class RelatedModelsTests(SimpleTestCase):
    def setUp(self):
        self.apps = Apps(["migrations.related_models_app"])

    def create_model(
        self, name, foreign_keys=[], bases=(), abstract=False, proxy=False
    ):
        test_name = "related_models_app"
        assert not (abstract and proxy)
        meta_contents = {
            "abstract": abstract,
            "app_label": test_name,
            "apps": self.apps,
            "proxy": proxy,
        }
        meta = type("Meta", (), meta_contents)
        if not bases:
            bases = (models.Model,)
        body = {
            "Meta": meta,
            "__module__": "__fake__",
        }
        fname_base = fname = "%s_%%d" % name.lower()
        for i, fk in enumerate(foreign_keys, 1):
            fname = fname_base % i
            body[fname] = fk
        return type(name, bases, body)

    def assertRelated(self, model, needle):
        self.assertEqual(
            get_related_models_recursive(model),
            {(n._meta.app_label, n._meta.model_name) for n in needle},
        )

    def test_unrelated(self):
        A = self.create_model("A")
        B = self.create_model("B")
        self.assertRelated(A, [])
        self.assertRelated(B, [])

    def test_direct_fk(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("B", models.CASCADE)]
        )
        B = self.create_model("B")
        self.assertRelated(A, [B])
        self.assertRelated(B, [A])

    def test_direct_hidden_fk(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("B", models.CASCADE, related_name="+")]
        )
        B = self.create_model("B")
        self.assertRelated(A, [B])
        self.assertRelated(B, [A])

    def test_fk_through_proxy(self):
        A = self.create_model("A")
        B = self.create_model("B", bases=(A,), proxy=True)
        C = self.create_model("C", bases=(B,), proxy=True)
        D = self.create_model(
            "D", foreign_keys=[models.ForeignKey("C", models.CASCADE)]
        )
        self.assertRelated(A, [B, C, D])
        self.assertRelated(B, [A, C, D])
        self.assertRelated(C, [A, B, D])
        self.assertRelated(D, [A, B, C])

    def test_nested_fk(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("B", models.CASCADE)]
        )
        B = self.create_model(
            "B", foreign_keys=[models.ForeignKey("C", models.CASCADE)]
        )
        C = self.create_model("C")
        self.assertRelated(A, [B, C])
        self.assertRelated(B, [A, C])
        self.assertRelated(C, [A, B])

    def test_two_sided(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("B", models.CASCADE)]
        )
        B = self.create_model(
            "B", foreign_keys=[models.ForeignKey("A", models.CASCADE)]
        )
        self.assertRelated(A, [B])
        self.assertRelated(B, [A])

    def test_circle(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("B", models.CASCADE)]
        )
        B = self.create_model(
            "B", foreign_keys=[models.ForeignKey("C", models.CASCADE)]
        )
        C = self.create_model(
            "C", foreign_keys=[models.ForeignKey("A", models.CASCADE)]
        )
        self.assertRelated(A, [B, C])
        self.assertRelated(B, [A, C])
        self.assertRelated(C, [A, B])

    def test_base(self):
        A = self.create_model("A")
        B = self.create_model("B", bases=(A,))
        self.assertRelated(A, [B])
        self.assertRelated(B, [A])

    def test_nested_base(self):
        A = self.create_model("A")
        B = self.create_model("B", bases=(A,))
        C = self.create_model("C", bases=(B,))
        self.assertRelated(A, [B, C])
        self.assertRelated(B, [A, C])
        self.assertRelated(C, [A, B])

    def test_multiple_bases(self):
        A = self.create_model("A")
        B = self.create_model("B")
        C = self.create_model(
            "C",
            bases=(
                A,
                B,
            ),
        )
        self.assertRelated(A, [B, C])
        self.assertRelated(B, [A, C])
        self.assertRelated(C, [A, B])

    def test_multiple_nested_bases(self):
        A = self.create_model("A")
        B = self.create_model("B")
        C = self.create_model(
            "C",
            bases=(
                A,
                B,
            ),
        )
        D = self.create_model("D")
        E = self.create_model("E", bases=(D,))
        F = self.create_model(
            "F",
            bases=(
                C,
                E,
            ),
        )
        Y = self.create_model("Y")
        Z = self.create_model("Z", bases=(Y,))
        self.assertRelated(A, [B, C, D, E, F])
        self.assertRelated(B, [A, C, D, E, F])
        self.assertRelated(C, [A, B, D, E, F])
        self.assertRelated(D, [A, B, C, E, F])
        self.assertRelated(E, [A, B, C, D, F])
        self.assertRelated(F, [A, B, C, D, E])
        self.assertRelated(Y, [Z])
        self.assertRelated(Z, [Y])

    def test_base_to_base_fk(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("Y", models.CASCADE)]
        )
        B = self.create_model("B", bases=(A,))
        Y = self.create_model("Y")
        Z = self.create_model("Z", bases=(Y,))
        self.assertRelated(A, [B, Y, Z])
        self.assertRelated(B, [A, Y, Z])
        self.assertRelated(Y, [A, B, Z])
        self.assertRelated(Z, [A, B, Y])

    def test_base_to_subclass_fk(self):
        A = self.create_model(
            "A", foreign_keys=[models.ForeignKey("Z", models.CASCADE)]
        )
        B = self.create_model("B", bases=(A,))
        Y = self.create_model("Y")
        Z = self.create_model("Z", bases=(Y,))
        self.assertRelated(A, [B, Y, Z])
        self.assertRelated(B, [A, Y, Z])
        self.assertRelated(Y, [A, B, Z])
        self.assertRelated(Z, [A, B, Y])

    def test_direct_m2m(self):
        A = self.create_model("A", foreign_keys=[models.ManyToManyField("B")])
        B = self.create_model("B")
        self.assertRelated(A, [A.a_1.rel.through, B])
        self.assertRelated(B, [A, A.a_1.rel.through])

    def test_direct_m2m_self(self):
        A = self.create_model("A", foreign_keys=[models.ManyToManyField("A")])
        self.assertRelated(A, [A.a_1.rel.through])

    def test_intermediate_m2m_self(self):
        A = self.create_model(
            "A", foreign_keys=[models.ManyToManyField("A", through="T")]
        )
        T = self.create_model(
            "T",
            foreign_keys=[
                models.ForeignKey("A", models.CASCADE),
                models.ForeignKey("A", models.CASCADE),
            ],
        )
        self.assertRelated(A, [T])
        self.assertRelated(T, [A])

    def test_intermediate_m2m(self):
        A = self.create_model(
            "A", foreign_keys=[models.ManyToManyField("B", through="T")]
        )
        B = self.create_model("B")
        T = self.create_model(
            "T",
            foreign_keys=[
                models.ForeignKey("A", models.CASCADE),
                models.ForeignKey("B", models.CASCADE),
            ],
        )
        self.assertRelated(A, [B, T])
        self.assertRelated(B, [A, T])
        self.assertRelated(T, [A, B])

    def test_intermediate_m2m_extern_fk(self):
        A = self.create_model(
            "A", foreign_keys=[models.ManyToManyField("B", through="T")]
        )
        B = self.create_model("B")
        Z = self.create_model("Z")
        T = self.create_model(
            "T",
            foreign_keys=[
                models.ForeignKey("A", models.CASCADE),
                models.ForeignKey("B", models.CASCADE),
                models.ForeignKey("Z", models.CASCADE),
            ],
        )
        self.assertRelated(A, [B, T, Z])
        self.assertRelated(B, [A, T, Z])
        self.assertRelated(T, [A, B, Z])
        self.assertRelated(Z, [A, B, T])

    def test_intermediate_m2m_base(self):
        A = self.create_model(
            "A", foreign_keys=[models.ManyToManyField("B", through="T")]
        )
        B = self.create_model("B")
        S = self.create_model("S")
        T = self.create_model(
            "T",
            foreign_keys=[
                models.ForeignKey("A", models.CASCADE),
                models.ForeignKey("B", models.CASCADE),
            ],
            bases=(S,),
        )
        self.assertRelated(A, [B, S, T])
        self.assertRelated(B, [A, S, T])
        self.assertRelated(S, [A, B, T])
        self.assertRelated(T, [A, B, S])

    def test_generic_fk(self):
        A = self.create_model(
            "A",
            foreign_keys=[
                models.ForeignKey("B", models.CASCADE),
                GenericForeignKey(),
            ],
        )
        B = self.create_model(
            "B",
            foreign_keys=[
                models.ForeignKey("C", models.CASCADE),
            ],
        )
        self.assertRelated(A, [B])
        self.assertRelated(B, [A])

    def test_abstract_base(self):
        A = self.create_model("A", abstract=True)
        B = self.create_model("B", bases=(A,))
        self.assertRelated(A, [B])
        self.assertRelated(B, [])

    def test_nested_abstract_base(self):
        A = self.create_model("A", abstract=True)
        B = self.create_model("B", bases=(A,), abstract=True)
        C = self.create_model("C", bases=(B,))
        self.assertRelated(A, [B, C])
        self.assertRelated(B, [C])
        self.assertRelated(C, [])

    def test_proxy_base(self):
        A = self.create_model("A")
        B = self.create_model("B", bases=(A,), proxy=True)
        self.assertRelated(A, [B])
        self.assertRelated(B, [])

    def test_nested_proxy_base(self):
        A = self.create_model("A")
        B = self.create_model("B", bases=(A,), proxy=True)
        C = self.create_model("C", bases=(B,), proxy=True)
        self.assertRelated(A, [B, C])
        self.assertRelated(B, [C])
        self.assertRelated(C, [])

    def test_multiple_mixed_bases(self):
        A = self.create_model("A", abstract=True)
        M = self.create_model("M")
        P = self.create_model("P")
        Q = self.create_model("Q", bases=(P,), proxy=True)
        Z = self.create_model("Z", bases=(A, M, Q))
        # M has a pointer O2O field p_ptr to P
        self.assertRelated(A, [M, P, Q, Z])
        self.assertRelated(M, [P, Q, Z])
        self.assertRelated(P, [M, Q, Z])
        self.assertRelated(Q, [M, P, Z])
        self.assertRelated(Z, [M, P, Q])
