from __future__ import absolute_import

from django.test import TestCase
from django.utils import six

from .models import (ObjectQuerySet, RelatedObject, Person, Book, Car, PersonManager,
    PublishedBookManager)


class CustomManagerTests(TestCase):
    def test_manager(self):
        p1 = Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        p2 = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False)

        self.assertQuerysetEqual(
            Person.objects.get_fun_people(), [
                "Bugs Bunny"
            ],
            six.text_type
        )
        # The RelatedManager used on the 'books' descriptor extends the default
        # manager
        self.assertTrue(isinstance(p2.books, PublishedBookManager))

        b1 = Book.published_objects.create(
            title="How to program", author="Rodney Dangerfield", is_published=True
        )
        b2 = Book.published_objects.create(
            title="How to be smart", author="Albert Einstein", is_published=False
        )

        # The default manager, "objects", doesn't exist, because a custom one
        # was provided.
        self.assertRaises(AttributeError, lambda: Book.objects)

        # The RelatedManager used on the 'authors' descriptor extends the
        # default manager
        self.assertTrue(isinstance(b2.authors, PersonManager))

        self.assertQuerysetEqual(
            Book.published_objects.all(), [
                "How to program",
            ],
            lambda b: b.title
        )

        c1 = Car.cars.create(name="Corvette", mileage=21, top_speed=180)
        c2 = Car.cars.create(name="Neon", mileage=31, top_speed=100)

        self.assertQuerysetEqual(
            Car.cars.order_by("name"), [
                "Corvette",
                "Neon",
            ],
            lambda c: c.name
        )

        self.assertQuerysetEqual(
            Car.fast_cars.all(), [
                "Corvette",
            ],
            lambda c: c.name
        )

        # Each model class gets a "_default_manager" attribute, which is a
        # reference to the first manager defined in the class. In this case,
        # it's "cars".

        self.assertQuerysetEqual(
            Car._default_manager.order_by("name"), [
                "Corvette",
                "Neon",
            ],
            lambda c: c.name
        )

    def test_related_manager(self):
        """
        Make sure un-saved object's related managers always return an instance
        of the same class the manager's `get_query_set` returns. Refs #19652.
        """
        rel_qs = RelatedObject().objs.all()
        self.assertIsInstance(rel_qs, ObjectQuerySet)
        with self.assertNumQueries(0):
            self.assertFalse(rel_qs.exists())
