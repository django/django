from __future__ import absolute_import

from operator import attrgetter

from django.core.exceptions import FieldError
from django.test import TestCase

from .models import (Chef, CommonInfo, ItalianRestaurant, ParkingLot, Place,
    Post, Restaurant, Student, StudentWorker, Supplier, Worker, MixinModel)


class ModelInheritanceTests(TestCase):
    def test_abstract(self):
        # The Student and Worker models both have 'name' and 'age' fields on
        # them and inherit the __unicode__() method, just as with normal Python
        # subclassing. This is useful if you want to factor out common
        # information for programming purposes, but still completely
        # independent separate models at the database level.
        w1 = Worker.objects.create(name="Fred", age=35, job="Quarry worker")
        w2 = Worker.objects.create(name="Barney", age=34, job="Quarry worker")

        s = Student.objects.create(name="Pebbles", age=5, school_class="1B")

        self.assertEqual(unicode(w1), "Worker Fred")
        self.assertEqual(unicode(s), "Student Pebbles")

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

        # A StudentWorker which does not exist is both a Student and Worker
        # which does not exist.
        self.assertRaises(Student.DoesNotExist,
            StudentWorker.objects.get, pk=12321321
        )
        self.assertRaises(Worker.DoesNotExist,
            StudentWorker.objects.get, pk=12321321
        )

        # MultipleObjectsReturned is also inherited.
        # This is written out "long form", rather than using __init__/create()
        # because of a bug with diamond inheritance (#10808)
        sw1 = StudentWorker()
        sw1.name = "Wilma"
        sw1.age = 35
        sw1.save()
        sw2 = StudentWorker()
        sw2.name = "Betty"
        sw2.age = 24
        sw2.save()

        self.assertRaises(Student.MultipleObjectsReturned,
            StudentWorker.objects.get, pk__lt=sw2.pk + 100
        )
        self.assertRaises(Worker.MultipleObjectsReturned,
            StudentWorker.objects.get, pk__lt=sw2.pk + 100
        )

    def test_multiple_table(self):
        post = Post.objects.create(title="Lorem Ipsum")
        # The Post model has distinct accessors for the Comment and Link models.
        post.attached_comment_set.create(content="Save $ on V1agr@", is_spam=True)
        post.attached_link_set.create(
            content="The Web framework for perfections with deadlines.",
            url="http://www.djangoproject.com/"
        )

        # The Post model doesn't have an attribute called
        # 'attached_%(class)s_set'.
        self.assertRaises(AttributeError,
            getattr, post, "attached_%(class)s_set"
        )

        # The Place/Restaurant/ItalianRestaurant models all exist as
        # independent models. However, the subclasses also have transparent
        # access to the fields of their ancestors.
        # Create a couple of Places.
        p1 = Place.objects.create(name="Master Shakes", address="666 W. Jersey")
        p2 = Place.objects.create(name="Ace Harware", address="1013 N. Ashland")

        # Test constructor for Restaurant.
        r = Restaurant.objects.create(
            name="Demon Dogs",
            address="944 W. Fullerton",
            serves_hot_dogs=True,
            serves_pizza=False,
            rating=2
        )
        # Test the constructor for ItalianRestaurant.
        c = Chef.objects.create(name="Albert")
        ir = ItalianRestaurant.objects.create(
            name="Ristorante Miron",
            address="1234 W. Ash",
            serves_hot_dogs=False,
            serves_pizza=False,
            serves_gnocchi=True,
            rating=4,
            chef=c
        )
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(address="1234 W. Ash"), [
                "Ristorante Miron",
            ],
            attrgetter("name")
        )
        ir.address = "1234 W. Elm"
        ir.save()
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(address="1234 W. Elm"), [
                "Ristorante Miron",
            ],
            attrgetter("name")
        )

        # Make sure Restaurant and ItalianRestaurant have the right fields in
        # the right order.
        self.assertEqual(
            [f.name for f in Restaurant._meta.fields],
            ["id", "name", "address", "place_ptr", "rating", "serves_hot_dogs", "serves_pizza", "chef"]
        )
        self.assertEqual(
            [f.name for f in ItalianRestaurant._meta.fields],
            ["id", "name", "address", "place_ptr", "rating", "serves_hot_dogs", "serves_pizza", "chef", "restaurant_ptr", "serves_gnocchi"],
        )
        self.assertEqual(Restaurant._meta.ordering, ["-rating"])

        # Even though p.supplier for a Place 'p' (a parent of a Supplier), a
        # Restaurant object cannot access that reverse relation, since it's not
        # part of the Place-Supplier Hierarchy.
        self.assertQuerysetEqual(Place.objects.filter(supplier__name="foo"), [])
        self.assertRaises(FieldError,
            Restaurant.objects.filter, supplier__name="foo"
        )

        # Parent fields can be used directly in filters on the child model.
        self.assertQuerysetEqual(
            Restaurant.objects.filter(name="Demon Dogs"), [
                "Demon Dogs",
            ],
            attrgetter("name")
        )
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.filter(address="1234 W. Elm"), [
                "Ristorante Miron",
            ],
            attrgetter("name")
        )

        # Filters against the parent model return objects of the parent's type.
        p = Place.objects.get(name="Demon Dogs")
        self.assertIs(type(p), Place)

        # Since the parent and child are linked by an automatically created
        # OneToOneField, you can get from the parent to the child by using the
        # child's name.
        self.assertEqual(
            p.restaurant, Restaurant.objects.get(name="Demon Dogs")
        )
        self.assertEqual(
            Place.objects.get(name="Ristorante Miron").restaurant.italianrestaurant,
            ItalianRestaurant.objects.get(name="Ristorante Miron")
        )
        self.assertEqual(
            Restaurant.objects.get(name="Ristorante Miron").italianrestaurant,
            ItalianRestaurant.objects.get(name="Ristorante Miron")
        )

        # This won't work because the Demon Dogs restaurant is not an Italian
        # restaurant.
        self.assertRaises(ItalianRestaurant.DoesNotExist,
            lambda: p.restaurant.italianrestaurant
        )
        # An ItalianRestaurant which does not exist is also a Place which does
        # not exist.
        self.assertRaises(Place.DoesNotExist,
            ItalianRestaurant.objects.get, name="The Noodle Void"
        )
        # MultipleObjectsReturned is also inherited.
        self.assertRaises(Place.MultipleObjectsReturned,
            Restaurant.objects.get, id__lt=12321
        )

        # Related objects work just as they normally do.
        s1 = Supplier.objects.create(name="Joe's Chickens", address="123 Sesame St")
        s1.customers = [r, ir]
        s2 = Supplier.objects.create(name="Luigi's Pasta", address="456 Sesame St")
        s2.customers = [ir]

        # This won't work because the Place we select is not a Restaurant (it's
        # a Supplier).
        p = Place.objects.get(name="Joe's Chickens")
        self.assertRaises(Restaurant.DoesNotExist,
            lambda: p.restaurant
        )

        self.assertEqual(p.supplier, s1)
        self.assertQuerysetEqual(
            ir.provider.order_by("-name"), [
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

        park1 = ParkingLot.objects.create(
            name="Main St", address="111 Main St", main_site=s1
        )
        park2 = ParkingLot.objects.create(
            name="Well Lit", address="124 Sesame St", main_site=ir
        )

        self.assertEqual(
            Restaurant.objects.get(lot__name="Well Lit").name,
            "Ristorante Miron"
        )

        # The update() command can update fields in parent and child classes at
        # once (although it executed multiple SQL queries to do so).
        rows = Restaurant.objects.filter(
            serves_hot_dogs=True, name__contains="D"
        ).update(
            name="Demon Puppies", serves_hot_dogs=False
        )
        self.assertEqual(rows, 1)

        r1 = Restaurant.objects.get(pk=r.pk)
        self.assertFalse(r1.serves_hot_dogs)
        self.assertEqual(r1.name, "Demon Puppies")

        # The values() command also works on fields from parent models.
        self.assertQuerysetEqual(
            ItalianRestaurant.objects.values("name", "rating"), [
                {"rating": 4, "name": "Ristorante Miron"}
            ],
            lambda o: o
        )

        # select_related works with fields from the parent object as if they
        # were a normal part of the model.
        self.assertNumQueries(2,
            lambda: ItalianRestaurant.objects.all()[0].chef
        )
        self.assertNumQueries(1,
            lambda: ItalianRestaurant.objects.select_related("chef")[0].chef
        )

    def test_mixin_init(self):
        m = MixinModel()
        self.assertEqual(m.other_attr, 1)
