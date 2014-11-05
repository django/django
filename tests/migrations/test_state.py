from django.apps.registry import Apps
from django.db import models
from django.db.migrations.state import ProjectState, ModelState, InvalidBasesError
from django.test import TestCase

from .models import (FoodManager, FoodQuerySet, ModelWithCustomBase,
    NoMigrationFoodManager)


class StateTests(TestCase):
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
                index_together = ["bio", "age"]

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
            author = models.ForeignKey(Author)
            contributors = models.ManyToManyField(Author)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                verbose_name = "tome"
                db_table = "test_tome"

        class Food(models.Model):

            food_mgr = FoodManager('a', 'b')
            food_qs = FoodQuerySet.as_manager()
            food_no_mgr = NoMigrationFoodManager('x', 'y')

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class FoodNoManagers(models.Model):

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class FoodNoDefaultManager(models.Model):

            food_no_mgr = NoMigrationFoodManager('x', 'y')
            food_mgr = FoodManager('a', 'b')
            food_qs = FoodQuerySet.as_manager()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        mgr1 = FoodManager('a', 'b')
        mgr2 = FoodManager('x', 'y', c=3, d=4)

        class FoodOrderedManagers(models.Model):
            # The managers on this model should be orderd by their creation
            # counter and not by the order in model body

            food_no_mgr = NoMigrationFoodManager('x', 'y')
            food_mgr2 = mgr2
            food_mgr1 = mgr1

            class Meta:
                app_label = "migrations"
                apps = new_apps

        project_state = ProjectState.from_apps(new_apps)
        author_state = project_state.models['migrations', 'author']
        author_proxy_state = project_state.models['migrations', 'authorproxy']
        sub_author_state = project_state.models['migrations', 'subauthor']
        book_state = project_state.models['migrations', 'book']
        food_state = project_state.models['migrations', 'food']
        food_no_managers_state = project_state.models['migrations', 'foodnomanagers']
        food_no_default_manager_state = project_state.models['migrations', 'foodnodefaultmanager']
        food_order_manager_state = project_state.models['migrations', 'foodorderedmanagers']

        self.assertEqual(author_state.app_label, "migrations")
        self.assertEqual(author_state.name, "Author")
        self.assertEqual([x for x, y in author_state.fields], ["id", "name", "bio", "age"])
        self.assertEqual(author_state.fields[1][1].max_length, 255)
        self.assertEqual(author_state.fields[2][1].null, False)
        self.assertEqual(author_state.fields[3][1].null, True)
        self.assertEqual(author_state.options, {"unique_together": {("name", "bio")}, "index_together": {("bio", "age")}})
        self.assertEqual(author_state.bases, (models.Model, ))

        self.assertEqual(book_state.app_label, "migrations")
        self.assertEqual(book_state.name, "Book")
        self.assertEqual([x for x, y in book_state.fields], ["id", "title", "author", "contributors"])
        self.assertEqual(book_state.fields[1][1].max_length, 1000)
        self.assertEqual(book_state.fields[2][1].null, False)
        self.assertEqual(book_state.fields[3][1].__class__.__name__, "ManyToManyField")
        self.assertEqual(book_state.options, {"verbose_name": "tome", "db_table": "test_tome"})
        self.assertEqual(book_state.bases, (models.Model, ))

        self.assertEqual(author_proxy_state.app_label, "migrations")
        self.assertEqual(author_proxy_state.name, "AuthorProxy")
        self.assertEqual(author_proxy_state.fields, [])
        self.assertEqual(author_proxy_state.options, {"proxy": True, "ordering": ["name"]})
        self.assertEqual(author_proxy_state.bases, ("migrations.author", ))

        self.assertEqual(sub_author_state.app_label, "migrations")
        self.assertEqual(sub_author_state.name, "SubAuthor")
        self.assertEqual(len(sub_author_state.fields), 2)
        self.assertEqual(sub_author_state.bases, ("migrations.author", ))

        # The default manager is used in migrations
        self.assertEqual([name for name, mgr in food_state.managers], ['food_mgr'])
        self.assertEqual(food_state.managers[0][1].args, ('a', 'b', 1, 2))

        # No explicit managers defined. Migrations will fall back to the default
        self.assertEqual(food_no_managers_state.managers, [])

        # food_mgr is used in migration but isn't the default mgr, hence add the
        # default
        self.assertEqual([name for name, mgr in food_no_default_manager_state.managers],
                         ['food_no_mgr', 'food_mgr'])
        self.assertEqual(food_no_default_manager_state.managers[0][1].__class__, models.Manager)
        self.assertIsInstance(food_no_default_manager_state.managers[1][1], FoodManager)

        self.assertEqual([name for name, mgr in food_order_manager_state.managers],
                         ['food_mgr1', 'food_mgr2'])
        self.assertEqual([mgr.args for name, mgr in food_order_manager_state.managers],
                         [('a', 'b', 1, 2), ('x', 'y', 3, 4)])

    def test_render(self):
        """
        Tests rendering a ProjectState into an Apps.
        """
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            app_label="migrations",
            name="Tag",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("hidden", models.BooleanField()),
            ],
        ))
        project_state.add_model_state(ModelState(
            app_label="migrations",
            name="SubTag",
            fields=[
                ('tag_ptr', models.OneToOneField(
                    auto_created=True,
                    primary_key=True,
                    to_field='id',
                    serialize=False,
                    to='migrations.Tag',
                )),
                ("awesome", models.BooleanField()),
            ],
            bases=("migrations.Tag",),
        ))

        base_mgr = models.Manager()
        mgr1 = FoodManager('a', 'b')
        mgr2 = FoodManager('x', 'y', c=3, d=4)
        project_state.add_model_state(ModelState(
            app_label="migrations",
            name="Food",
            fields=[
                ("id", models.AutoField(primary_key=True)),
            ],
            managers=[
                # The ordering we really want is objects, mgr1, mgr2
                ('default', base_mgr),
                ('food_mgr2', mgr2),
                ('food_mgr1', mgr1),
            ]
        ))

        new_apps = project_state.apps
        self.assertEqual(new_apps.get_model("migrations", "Tag")._meta.get_field_by_name("name")[0].max_length, 100)
        self.assertEqual(new_apps.get_model("migrations", "Tag")._meta.get_field_by_name("hidden")[0].null, False)

        self.assertEqual(len(new_apps.get_model("migrations", "SubTag")._meta.local_fields), 2)

        Food = new_apps.get_model("migrations", "Food")
        managers = sorted(Food._meta.managers)
        self.assertEqual([mgr.name for _, mgr, _ in managers],
                         ['default', 'food_mgr1', 'food_mgr2'])
        self.assertEqual([mgr.__class__ for _, mgr, _ in managers],
                         [models.Manager, FoodManager, FoodManager])
        self.assertIs(managers[0][1], Food._default_manager)

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
        self.assertSequenceEqual(ModelState.from_model(FooBar).bases, ['migrations.foo', 'migrations.bar'])
        ModelState.from_model(SubFooBar).render(apps)
        self.assertSequenceEqual(ModelState.from_model(SubFooBar).bases, ['migrations.foobar'])

    def test_render_project_dependencies(self):
        """
        Tests that the ProjectState render method correctly renders models
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
        project_state.add_model_state(ModelState.from_model(A))
        project_state.add_model_state(ModelState.from_model(B))
        project_state.add_model_state(ModelState.from_model(C))
        project_state.add_model_state(ModelState.from_model(D))
        project_state.add_model_state(ModelState.from_model(E))
        project_state.add_model_state(ModelState.from_model(F))
        final_apps = project_state.apps
        self.assertEqual(len(final_apps.get_models()), 6)

        # Now make an invalid ProjectState and make sure it fails
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(A))
        project_state.add_model_state(ModelState.from_model(B))
        project_state.add_model_state(ModelState.from_model(C))
        project_state.add_model_state(ModelState.from_model(F))
        with self.assertRaises(InvalidBasesError):
            project_state.apps

    def test_render_unique_app_labels(self):
        """
        Tests that the ProjectState render method doesn't raise an
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
        project_state.add_model_state(ModelState.from_model(A))
        project_state.add_model_state(ModelState.from_model(B))
        self.assertEqual(len(project_state.apps.get_models()), 2)

    def test_equality(self):
        """
        Tests that == and != are implemented correctly.
        """

        # Test two things that should be equal
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("hidden", models.BooleanField()),
            ],
            {},
            None,
        ))
        other_state = project_state.clone()
        self.assertEqual(project_state, project_state)
        self.assertEqual(project_state, other_state)
        self.assertEqual(project_state != project_state, False)
        self.assertEqual(project_state != other_state, False)

        # Make a very small change (max_len 99) and see if that affects it
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=99)),
                ("hidden", models.BooleanField()),
            ],
            {},
            None,
        ))
        self.assertNotEqual(project_state, other_state)
        self.assertEqual(project_state == other_state, False)

    def test_dangling_references_throw_error(self):
        new_apps = Apps()

        class Author(models.Model):
            name = models.TextField()

            class Meta:
                app_label = "migrations"
                apps = new_apps

        class Book(models.Model):
            author = models.ForeignKey(Author)

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
        project_state.add_model_state(ModelState.from_model(Author))
        project_state.add_model_state(ModelState.from_model(Book))
        project_state.add_model_state(ModelState.from_model(Magazine))
        self.assertEqual(len(project_state.apps.get_models()), 3)

        # now make an invalid one with a ForeignKey
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(Book))
        with self.assertRaises(ValueError):
            project_state.apps

        # and another with ManyToManyField
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(Magazine))
        with self.assertRaises(ValueError):
            project_state.apps

    def test_real_apps(self):
        """
        Tests that including real apps can resolve dangling FK errors.
        This test relies on the fact that contenttypes is always loaded.
        """
        new_apps = Apps()

        class TestModel(models.Model):
            ct = models.ForeignKey("contenttypes.ContentType")

            class Meta:
                app_label = "migrations"
                apps = new_apps

        # If we just stick it into an empty state it should fail
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(TestModel))
        with self.assertRaises(ValueError):
            project_state.apps

        # If we include the real app it should succeed
        project_state = ProjectState(real_apps=["contenttypes"])
        project_state.add_model_state(ModelState.from_model(TestModel))
        rendered_state = project_state.apps
        self.assertEqual(
            len([x for x in rendered_state.get_models() if x._meta.app_label == "migrations"]),
            1,
        )

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
            author = models.ForeignKey(Author)

            class Meta:
                app_label = "migrations"
                apps = new_apps
                order_with_respect_to = "author"

        # Make a valid ProjectState and render it
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(Author))
        project_state.add_model_state(ModelState.from_model(Book))
        self.assertEqual(
            [name for name, field in project_state.models["migrations", "book"].fields],
            ["id", "author"],
        )


class ModelStateTests(TestCase):
    def test_custom_model_base(self):
        state = ModelState.from_model(ModelWithCustomBase)
        self.assertEqual(state.bases, (models.Model,))

    def test_bound_field_sanity_check(self):
        field = models.CharField(max_length=1)
        field.model = models.Model
        with self.assertRaisesMessage(ValueError,
                'ModelState.fields cannot be bound to a model - "field" is.'):
            ModelState('app', 'Model', [('field', field)])

    def test_fields_immutability(self):
        """
        Tests that rendering a model state doesn't alter its internal fields.
        """
        apps = Apps()
        field = models.CharField(max_length=1)
        state = ModelState('app', 'Model', [('name', field)])
        Model = state.render(apps)
        self.assertNotEqual(Model._meta.get_field('name'), field)

    def test_repr(self):
        field = models.CharField(max_length=1)
        state = ModelState('app', 'Model', [('name', field)], bases=['app.A', 'app.B', 'app.C'])
        self.assertEqual(repr(state), "<ModelState: 'app.Model'>")

        project_state = ProjectState()
        project_state.add_model_state(state)
        with self.assertRaisesMessage(InvalidBasesError, "Cannot resolve bases for [<ModelState: 'app.Model'>]"):
            project_state.apps
