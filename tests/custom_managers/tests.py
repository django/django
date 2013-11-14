from __future__ import unicode_literals

from django.test import TestCase
from django.utils import six

from .models import Person, Book, Car, PersonManager, PublishedBookManager


class CustomManagerTests(TestCase):
    def setUp(self):
        self.b1 = Book.published_objects.create(
            title="How to program", author="Rodney Dangerfield", is_published=True)
        self.b2 = Book.published_objects.create(
            title="How to be smart", author="Albert Einstein", is_published=False)
        self.p1 = Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        self.p2 = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False)

    def test_manager(self):
        # Test a custom `Manager` method.
        self.assertQuerysetEqual(
            Person.objects.get_fun_people(), [
                "Bugs Bunny"
            ],
            six.text_type
        )

        # Test that the methods of a custom `QuerySet` are properly
        # copied onto the default `Manager`.
        for manager in ['custom_queryset_default_manager',
                        'custom_queryset_custom_manager']:
            manager = getattr(Person, manager)

            # Copy public methods.
            manager.public_method()
            # Don't copy private methods.
            with self.assertRaises(AttributeError):
                manager._private_method()
            # Copy methods with `manager=True` even if they are private.
            manager._optin_private_method()
            # Don't copy methods with `manager=False` even if they are public.
            with self.assertRaises(AttributeError):
                manager.optout_public_method()

            # Test that the overridden method is called.
            queryset = manager.filter()
            self.assertQuerysetEqual(queryset, ["Bugs Bunny"], six.text_type)
            self.assertEqual(queryset._filter_CustomQuerySet, True)

            # Test that specialized querysets inherit from our custom queryset.
            queryset = manager.values_list('first_name', flat=True).filter()
            self.assertEqual(list(queryset), [six.text_type("Bugs")])
            self.assertEqual(queryset._filter_CustomQuerySet, True)

        # Test that the custom manager `__init__()` argument has been set.
        self.assertEqual(Person.custom_queryset_custom_manager.init_arg, 'hello')

        # Test that the custom manager method is only available on the manager.
        Person.custom_queryset_custom_manager.manager_only()
        with self.assertRaises(AttributeError):
            Person.custom_queryset_custom_manager.all().manager_only()

        # Test that the queryset method doesn't override the custom manager method.
        queryset = Person.custom_queryset_custom_manager.filter()
        self.assertQuerysetEqual(queryset, ["Bugs Bunny"], six.text_type)
        self.assertEqual(queryset._filter_CustomManager, True)

        # The RelatedManager used on the 'books' descriptor extends the default
        # manager
        self.assertIsInstance(self.p2.books, PublishedBookManager)

        # The default manager, "objects", doesn't exist, because a custom one
        # was provided.
        self.assertRaises(AttributeError, lambda: Book.objects)

        # The RelatedManager used on the 'authors' descriptor extends the
        # default manager
        self.assertIsInstance(self.b2.authors, PersonManager)

        self.assertQuerysetEqual(
            Book.published_objects.all(), [
                "How to program",
            ],
            lambda b: b.title
        )

        Car.cars.create(name="Corvette", mileage=21, top_speed=180)
        Car.cars.create(name="Neon", mileage=31, top_speed=100)

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

    def test_related_manager_fk(self):
        self.p1.favorite_book = self.b1
        self.p1.save()
        self.p2.favorite_book = self.b1
        self.p2.save()

        self.assertQuerysetEqual(
            self.b1.favorite_books.order_by('first_name').all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name
        )
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name
        )
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='fun_people').all(), [
                "Bugs",
            ],
            lambda c: c.first_name
        )

    def test_related_manager_gfk(self):
        self.p1.favorite_thing = self.b1
        self.p1.save()
        self.p2.favorite_thing = self.b1
        self.p2.save()

        self.assertQuerysetEqual(
            self.b1.favorite_things.order_by('first_name').all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name
        )
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name
        )
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='fun_people').all(), [
                "Bugs",
            ],
            lambda c: c.first_name
        )

    def test_related_manager_m2m(self):
        self.b1.authors.add(self.p1)
        self.b1.authors.add(self.p2)

        self.assertQuerysetEqual(
            self.b1.authors.order_by('first_name').all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name
        )
        self.assertQuerysetEqual(
            self.b1.authors(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name
        )
        self.assertQuerysetEqual(
            self.b1.authors(manager='fun_people').all(), [
                "Bugs",
            ],
            lambda c: c.first_name
        )
