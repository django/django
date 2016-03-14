from __future__ import unicode_literals

from operator import attrgetter

from django.core.exceptions import FieldError, ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import six

from .models import (
    Base, Chef, CommonInfo, Copy, GrandChild, GrandParent, ItalianRestaurant,
    MixinModel, ParkingLot, Place, Post, Restaurant, Student, SubBase,
    Supplier, Title, Worker,
)


class ModelInheritanceTests(TestCase):
    def test_abstract(self):
        # The Student and Worker models both have 'name' and 'age' fields on
        # them and inherit the __unicode__() method, just as with normal Python
        # subclassing. This is useful if you want to factor out common
        # information for programming purposes, but still completely
        # independent separate models at the database level.
        w1 = Worker.objects.create(name="Fred", age=35, job="Quarry worker")
        Worker.objects.create(name="Barney", age=34, job="Quarry worker")

        s = Student.objects.create(name="Pebbles", age=5, school_class="1B")

        self.assertEqual(six.text_type(w1), "Worker Fred")
        self.assertEqual(six.text_type(s), "Student Pebbles")

        # The children inherit the Meta class of their parents (if they don't
        # specify their own).
        self.assertQuerysetEqual(
            Worker.objects.values("name"), [
                {"name": "Barney"},
                {"name": "Fred"},
            ],
            lambda o: o
        )

        # Since Student does not subclass CommonInfo's Meta, it has the effect
        # of completely overriding it. So ordering by name doesn't take place
        # for Students.
        self.assertEqual(Student._meta.ordering, [])

        # However, the CommonInfo class cannot be used as a normal model (it
        # doesn't exist as a model).
        self.assertRaises(AttributeError, lambda: CommonInfo.objects.all())

    def test_reverse_relation_for_different_hierarchy_tree(self):
        # Even though p.supplier for a Place 'p' (a parent of a Supplier), a
        # Restaurant object cannot access that reverse relation, since it's not
        # part of the Place-Supplier Hierarchy.
        self.assertQuerysetEqual(Place.objects.filter(supplier__name="foo"), [])
        self.assertRaises(FieldError, Restaurant.objects.filter, supplier__name="foo")

    def test_model_with_distinct_accessors(self):
        # The Post model has distinct accessors for the Comment and Link models.
        post = Post.objects.create(title="Lorem Ipsum")
        post.attached_comment_set.create(content="Save $ on V1agr@", is_spam=True)
        post.attached_link_set.create(
            content="The Web framework for perfections with deadlines.",
            url="http://www.djangoproject.com/"
        )

        # The Post model doesn't have an attribute called
        # 'attached_%(class)s_set'.
        self.assertRaises(
            AttributeError, getattr, post, "attached_%(class)s_set"
        )

    def test_meta_fields_and_ordering(self):
        # Make sure Restaurant and ItalianRestaurant have the right fields in
        # the right order.
        self.assertEqual(
            [f.name for f in Restaurant._meta.fields],
            ["id", "name", "address", "place_ptr", "rating", "serves_hot_dogs",
             "serves_pizza", "chef"]
        )
        self.assertEqual(
            [f.name for f in ItalianRestaurant._meta.fields],
            ["id", "name", "address", "place_ptr", "rating", "serves_hot_dogs",
             "serves_pizza", "chef", "restaurant_ptr", "serves_gnocchi"],
        )
        self.assertEqual(Restaurant._meta.ordering, ["-rating"])

    def test_custompk_m2m(self):
        b = Base.objects.create()
        b.titles.add(Title.objects.create(title="foof"))
        s = SubBase.objects.create(sub_id=b.id)
        b = Base.objects.get(pk=s.id)
        self.assertNotEqual(b.pk, s.pk)
        # Low-level test for related_val
        self.assertEqual(s.titles.related_val, (s.id,))
        # Higher level test for correct query values (title foof not
        # accidentally found).
        self.assertQuerysetEqual(s.titles.all(), [])

    def test_update_parent_filtering(self):
        """
        Test that updating a field of a model subclass doesn't issue an UPDATE
        query constrained by an inner query.
        Refs #10399
        """
        supplier = Supplier.objects.create(
            name='Central market',
            address='610 some street',
        )
        # Capture the expected query in a database agnostic way
        with CaptureQueriesContext(connection) as captured_queries:
            Place.objects.filter(pk=supplier.pk).update(name=supplier.name)
        expected_sql = captured_queries[0]['sql']
        # Capture the queries executed when a subclassed model instance is saved.
        with CaptureQueriesContext(connection) as captured_queries:
            supplier.save(update_fields=('name',))
        for query in captured_queries:
            sql = query['sql']
            if 'UPDATE' in sql:
                self.assertEqual(expected_sql, sql)

    def test_eq(self):
        # Equality doesn't transfer in multitable inheritance.
        self.assertNotEqual(Place(id=1), Restaurant(id=1))
        self.assertNotEqual(Restaurant(id=1), Place(id=1))

    def test_mixin_init(self):
        m = MixinModel()
        self.assertEqual(m.other_attr, 1)


class ModelInheritanceDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.restaurant = Restaurant.objects.create(
            name="Demon Dogs",
            address="944 W. Fullerton",
            serves_hot_dogs=True,
            serves_pizza=False,
            rating=2,
        )

        chef = Chef.objects.create(name="Albert")
        cls.italian_restaurant = ItalianRestaurant.objects.create(
            name="Ristorante Miron",
            address="1234 W. Ash",
            serves_hot_dogs=False,
            serves_pizza=False,
            serves_gnocchi=True,
            rating=4,
            chef=chef,
        )

    def test_filter_inherited_model(self):
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(address="1234 W. Ash"), [
                "Ristorante Miron",
            ],
            attrgetter("name")
        )

    def test_update_inherited_model(self):
        self.italian_restaurant.address = "1234 W. Elm"
        self.italian_restaurant.save()
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(address="1234 W. Elm"), [
                "Ristorante Miron",
            ],
            attrgetter("name")
        )

    def test_parent_fields_available_for_filtering_in_child_model(self):
        # Parent fields can be used directly in filters on the child model.
        self.assertQuerysetEqual(
            Restaurant.objects.filter(name="Demon Dogs"), [
                "Demon Dogs",
            ],
            attrgetter("name")
        )
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(address="1234 W. Ash"), [
                "Ristorante Miron",
            ],
            attrgetter("name")
        )

    def test_filter_on_parent_returns_object_of_parent_type(self):
        # Filters against the parent model return objects of the parent's type.
        p = Place.objects.get(name="Demon Dogs")
        self.assertIs(type(p), Place)

    def test_parent_child_one_to_one_link(self):
        # Since the parent and child are linked by an automatically created
        # OneToOneField, you can get from the parent to the child by using the
        # child's name.
        self.assertEqual(
            Place.objects.get(name="Demon Dogs").restaurant,
            Restaurant.objects.get(name="Demon Dogs")
        )
        self.assertEqual(
            Place.objects.get(name="Ristorante Miron").restaurant.italianrestaurant,
            ItalianRestaurant.objects.get(name="Ristorante Miron")
        )
        self.assertEqual(
            Restaurant.objects.get(name="Ristorante Miron").italianrestaurant,
            ItalianRestaurant.objects.get(name="Ristorante Miron")
        )

    def test_parent_child_one_to_one_link_on_nonrelated_objects(self):
        # This won't work because the Demon Dogs restaurant is not an Italian
        # restaurant.
        self.assertRaises(
            ItalianRestaurant.DoesNotExist,
            lambda: Place.objects.get(name="Demon Dogs").restaurant.italianrestaurant
        )

    def test_inherited_does_not_exist_exception(self):
        # An ItalianRestaurant which does not exist is also a Place which does
        # not exist.
        self.assertRaises(
            Place.DoesNotExist,
            ItalianRestaurant.objects.get, name="The Noodle Void"
        )

    def test_inherited_multiple_objects_returned_exception(self):
        # MultipleObjectsReturned is also inherited.
        with self.assertRaises(Place.MultipleObjectsReturned):
            Restaurant.objects.get()

    def test_related_objects_for_inherited_models(self):
        # Related objects work just as they normally do.
        s1 = Supplier.objects.create(name="Joe's Chickens", address="123 Sesame St")
        s1.customers = [self.restaurant, self.italian_restaurant]
        s2 = Supplier.objects.create(name="Luigi's Pasta", address="456 Sesame St")
        s2.customers = [self.italian_restaurant]

        # This won't work because the Place we select is not a Restaurant (it's
        # a Supplier).
        p = Place.objects.get(name="Joe's Chickens")
        self.assertRaises(
            Restaurant.DoesNotExist, lambda: p.restaurant
        )

        self.assertEqual(p.supplier, s1)
        self.assertQuerysetEqual(
            self.italian_restaurant.provider.order_by("-name"), [
                "Luigi's Pasta",
                "Joe's Chickens"
            ],
            attrgetter("name")
        )
        self.assertQuerysetEqual(
            Restaurant.objects.filter(provider__name__contains="Chickens"), [
                "Ristorante Miron",
                "Demon Dogs",
            ],
            attrgetter("name")
        )
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(provider__name__contains="Chickens"), [
                "Ristorante Miron",
            ],
            attrgetter("name"),
        )

        ParkingLot.objects.create(
            name="Main St", address="111 Main St", main_site=s1
        )
        ParkingLot.objects.create(
            name="Well Lit", address="124 Sesame St", main_site=self.italian_restaurant
        )

        self.assertEqual(
            Restaurant.objects.get(lot__name="Well Lit").name,
            "Ristorante Miron"
        )

    def test_update_works_on_parent_and_child_models_at_once(self):
        # The update() command can update fields in parent and child classes at
        # once (although it executed multiple SQL queries to do so).
        rows = Restaurant.objects.filter(
            serves_hot_dogs=True, name__contains="D"
        ).update(
            name="Demon Puppies", serves_hot_dogs=False
        )
        self.assertEqual(rows, 1)

        r1 = Restaurant.objects.get(pk=self.restaurant.pk)
        self.assertFalse(r1.serves_hot_dogs)
        self.assertEqual(r1.name, "Demon Puppies")

    def test_values_works_on_parent_model_fields(self):
        # The values() command also works on fields from parent models.
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.values("name", "rating"), [
                {"rating": 4, "name": "Ristorante Miron"},
            ],
            lambda o: o
        )

    def test_select_related_works_on_parent_model_fields(self):
        # select_related works with fields from the parent object as if they
        # were a normal part of the model.
        self.assertNumQueries(
            2, lambda: ItalianRestaurant.objects.all()[0].chef
        )
        self.assertNumQueries(
            1, lambda: ItalianRestaurant.objects.select_related("chef")[0].chef
        )

    def test_select_related_defer(self):
        """
        #23370 - Should be able to defer child fields when using
        select_related() from parent to child.
        """
        qs = (Restaurant.objects
            .select_related("italianrestaurant")
            .defer("italianrestaurant__serves_gnocchi")
            .order_by("rating"))

        # Test that the field was actually deferred
        with self.assertNumQueries(2):
            objs = list(qs.all())
            self.assertTrue(objs[1].italianrestaurant.serves_gnocchi)

        # Test that model fields where assigned correct values
        self.assertEqual(qs[0].name, 'Demon Dogs')
        self.assertEqual(qs[0].rating, 2)
        self.assertEqual(qs[1].italianrestaurant.name, 'Ristorante Miron')
        self.assertEqual(qs[1].italianrestaurant.rating, 4)

    def test_update_query_counts(self):
        """
        Test that update queries do not generate non-necessary queries.
        Refs #18304.
        """
        with self.assertNumQueries(3):
            self.italian_restaurant.save()

    def test_filter_inherited_on_null(self):
        # Refs #12567
        Supplier.objects.create(
            name="Central market",
            address="610 some street",
        )
        self.assertQuerysetEqual(
            Place.objects.filter(supplier__isnull=False), [
                "Central market",
            ],
            attrgetter("name")
        )
        self.assertQuerysetEqual(
            Place.objects.filter(supplier__isnull=True).order_by("name"), [
                "Demon Dogs",
                "Ristorante Miron",
            ],
            attrgetter("name")
        )

    def test_exclude_inherited_on_null(self):
        # Refs #12567
        Supplier.objects.create(
            name="Central market",
            address="610 some street",
        )
        self.assertQuerysetEqual(
            Place.objects.exclude(supplier__isnull=False).order_by("name"), [
                "Demon Dogs",
                "Ristorante Miron",
            ],
            attrgetter("name")
        )
        self.assertQuerysetEqual(
            Place.objects.exclude(supplier__isnull=True), [
                "Central market",
            ],
            attrgetter("name")
        )


class InheritanceSameModelNameTests(TransactionTestCase):

    available_apps = ['model_inheritance']

    def setUp(self):
        # The Title model has distinct accessors for both
        # model_inheritance.Copy and model_inheritance_same_model_name.Copy
        # models.
        self.title = Title.objects.create(title='Lorem Ipsum')

    def test_inheritance_related_name(self):
        self.assertEqual(
            self.title.attached_model_inheritance_copy_set.create(
                content='Save $ on V1agr@',
                url='http://v1agra.com/',
                title='V1agra is spam',
            ), Copy.objects.get(
                content='Save $ on V1agr@',
            ))

    def test_inheritance_with_same_model_name(self):
        with self.modify_settings(
                INSTALLED_APPS={'append': ['model_inheritance.same_model_name']}):
            call_command('migrate', verbosity=0)
            from .same_model_name.models import Copy
            copy = self.title.attached_same_model_name_copy_set.create(
                content='The Web framework for perfectionists with deadlines.',
                url='http://www.djangoproject.com/',
                title='Django Rocks'
            )
            self.assertEqual(
                copy,
                Copy.objects.get(
                    content='The Web framework for perfectionists with deadlines.',
                ))
            # We delete the copy manually so that it doesn't block the flush
            # command under Oracle (which does not cascade deletions).
            copy.delete()

    def test_related_name_attribute_exists(self):
        # The Post model doesn't have an attribute called 'attached_%(app_label)s_%(class)s_set'.
        self.assertFalse(hasattr(self.title, 'attached_%(app_label)s_%(class)s_set'))


class InheritanceUniqueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.grand_parent = GrandParent.objects.create(
            email='grand_parent@example.com',
            first_name='grand',
            last_name='parent',
        )

    def test_unique(self):
        grand_child = GrandChild(
            email=self.grand_parent.email,
            first_name='grand',
            last_name='child',
        )
        msg = 'Grand parent with this Email already exists.'
        with self.assertRaisesMessage(ValidationError, msg):
            grand_child.validate_unique()

    def test_unique_together(self):
        grand_child = GrandChild(
            email='grand_child@example.com',
            first_name=self.grand_parent.first_name,
            last_name=self.grand_parent.last_name,
        )
        msg = 'Grand parent with this First name and Last name already exists.'
        with self.assertRaisesMessage(ValidationError, msg):
            grand_child.validate_unique()
