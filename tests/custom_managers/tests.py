from django.db import models
from django.test import TestCase

from .models import (
    Book, Car, CustomManager, CustomQuerySet, DeconstructibleCustomManager,
    FastCarAsBase, FastCarAsDefault, FunPerson, OneToOneRestrictedModel,
    Person, PersonFromAbstract, PersonManager, PublishedBookManager,
    RelatedModel, RestrictedModel,
)


class CustomManagerTests(TestCase):
    custom_manager_names = [
        'custom_queryset_default_manager',
        'custom_queryset_custom_manager',
    ]

    @classmethod
    def setUpTestData(cls):
        cls.b1 = Book.published_objects.create(
            title="How to program", author="Rodney Dangerfield", is_published=True)
        cls.b2 = Book.published_objects.create(
            title="How to be smart", author="Albert Einstein", is_published=False)

        cls.p1 = Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        cls.droopy = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False)

    def test_custom_manager_basic(self):
        """
        Test a custom Manager method.
        """
        self.assertQuerysetEqual(
            Person.objects.get_fun_people(), [
                "Bugs Bunny"
            ],
            str
        )

    def test_queryset_copied_to_default(self):
        """
        The methods of a custom QuerySet are properly copied onto the
        default Manager.
        """
        for manager_name in self.custom_manager_names:
            manager = getattr(Person, manager_name)

            # Public methods are copied
            manager.public_method()
            # Private methods are not copied
            with self.assertRaises(AttributeError):
                manager._private_method()

    def test_manager_honors_queryset_only(self):
        for manager_name in self.custom_manager_names:
            manager = getattr(Person, manager_name)
            # Methods with queryset_only=False are copied even if they are private.
            manager._optin_private_method()
            # Methods with queryset_only=True aren't copied even if they are public.
            with self.assertRaises(AttributeError):
                manager.optout_public_method()

    def test_manager_use_queryset_methods(self):
        """
        Custom manager will use the queryset methods
        """
        for manager_name in self.custom_manager_names:
            manager = getattr(Person, manager_name)
            queryset = manager.filter()
            self.assertQuerysetEqual(queryset, ["Bugs Bunny"], str)
            self.assertIs(queryset._filter_CustomQuerySet, True)

            # Specialized querysets inherit from our custom queryset.
            queryset = manager.values_list('first_name', flat=True).filter()
            self.assertEqual(list(queryset), ["Bugs"])
            self.assertIs(queryset._filter_CustomQuerySet, True)

            self.assertIsInstance(queryset.values(), CustomQuerySet)
            self.assertIsInstance(queryset.values().values(), CustomQuerySet)
            self.assertIsInstance(queryset.values_list().values(), CustomQuerySet)

    def test_init_args(self):
        """
        The custom manager __init__() argument has been set.
        """
        self.assertEqual(Person.custom_queryset_custom_manager.init_arg, 'hello')

    def test_manager_attributes(self):
        """
        Custom manager method is only available on the manager and not on
        querysets.
        """
        Person.custom_queryset_custom_manager.manager_only()
        with self.assertRaises(AttributeError):
            Person.custom_queryset_custom_manager.all().manager_only()

    def test_queryset_and_manager(self):
        """
        Queryset method doesn't override the custom manager method.
        """
        queryset = Person.custom_queryset_custom_manager.filter()
        self.assertQuerysetEqual(queryset, ["Bugs Bunny"], str)
        self.assertIs(queryset._filter_CustomManager, True)

    def test_related_manager(self):
        """
        The related managers extend the default manager.
        """
        self.assertIsInstance(self.droopy.books, PublishedBookManager)
        self.assertIsInstance(self.b2.authors, PersonManager)

    def test_no_objects(self):
        """
        The default manager, "objects", doesn't exist, because a custom one
        was provided.
        """
        with self.assertRaises(AttributeError):
            Book.objects

    def test_filtering(self):
        """
        Custom managers respond to usual filtering methods
        """
        self.assertQuerysetEqual(
            Book.published_objects.all(), [
                "How to program",
            ],
            lambda b: b.title
        )

    def test_fk_related_manager(self):
        Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_book=self.b1)
        Person.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_book=self.b1)
        FunPerson.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_book=self.b1)
        FunPerson.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_book=self.b1)

        self.assertQuerysetEqual(
            self.b1.favorite_books.order_by('first_name').all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.fun_people_favorite_books.all(), [
                "Bugs",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='fun_people').all(), [
                "Bugs",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_gfk_related_manager(self):
        Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_thing=self.b1)
        Person.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_thing=self.b1)
        FunPerson.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_thing=self.b1)
        FunPerson.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_thing=self.b1)

        self.assertQuerysetEqual(
            self.b1.favorite_things.all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.fun_people_favorite_things.all(), [
                "Bugs",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='fun_people').all(), [
                "Bugs",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_m2m_related_manager(self):
        bugs = Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        self.b1.authors.add(bugs)
        droopy = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False)
        self.b1.authors.add(droopy)
        bugs = FunPerson.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        self.b1.fun_authors.add(bugs)
        droopy = FunPerson.objects.create(first_name="Droopy", last_name="Dog", fun=False)
        self.b1.fun_authors.add(droopy)

        self.assertQuerysetEqual(
            self.b1.authors.order_by('first_name').all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.fun_authors.order_by('first_name').all(), [
                "Bugs",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.authors(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.authors(manager='fun_people').all(), [
                "Bugs",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_removal_through_default_fk_related_manager(self, bulk=True):
        bugs = FunPerson.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_book=self.b1)
        droopy = FunPerson.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_book=self.b1)

        self.b1.fun_people_favorite_books.remove(droopy, bulk=bulk)
        self.assertQuerysetEqual(
            FunPerson._base_manager.filter(favorite_book=self.b1), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

        self.b1.fun_people_favorite_books.remove(bugs, bulk=bulk)
        self.assertQuerysetEqual(
            FunPerson._base_manager.filter(favorite_book=self.b1), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        bugs.favorite_book = self.b1
        bugs.save()

        self.b1.fun_people_favorite_books.clear(bulk=bulk)
        self.assertQuerysetEqual(
            FunPerson._base_manager.filter(favorite_book=self.b1), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_slow_removal_through_default_fk_related_manager(self):
        self.test_removal_through_default_fk_related_manager(bulk=False)

    def test_removal_through_specified_fk_related_manager(self, bulk=True):
        Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_book=self.b1)
        droopy = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_book=self.b1)

        # The fun manager DOESN'T remove boring people.
        self.b1.favorite_books(manager='fun_people').remove(droopy, bulk=bulk)
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        # The boring manager DOES remove boring people.
        self.b1.favorite_books(manager='boring_people').remove(droopy, bulk=bulk)
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='boring_people').all(), [
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        droopy.favorite_book = self.b1
        droopy.save()

        # The fun manager ONLY clears fun people.
        self.b1.favorite_books(manager='fun_people').clear(bulk=bulk)
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.favorite_books(manager='fun_people').all(), [
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_slow_removal_through_specified_fk_related_manager(self):
        self.test_removal_through_specified_fk_related_manager(bulk=False)

    def test_removal_through_default_gfk_related_manager(self, bulk=True):
        bugs = FunPerson.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_thing=self.b1)
        droopy = FunPerson.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_thing=self.b1)

        self.b1.fun_people_favorite_things.remove(droopy, bulk=bulk)
        self.assertQuerysetEqual(
            FunPerson._base_manager.order_by('first_name').filter(favorite_thing_id=self.b1.pk), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

        self.b1.fun_people_favorite_things.remove(bugs, bulk=bulk)
        self.assertQuerysetEqual(
            FunPerson._base_manager.order_by('first_name').filter(favorite_thing_id=self.b1.pk), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        bugs.favorite_book = self.b1
        bugs.save()

        self.b1.fun_people_favorite_things.clear(bulk=bulk)
        self.assertQuerysetEqual(
            FunPerson._base_manager.order_by('first_name').filter(favorite_thing_id=self.b1.pk), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_slow_removal_through_default_gfk_related_manager(self):
        self.test_removal_through_default_gfk_related_manager(bulk=False)

    def test_removal_through_specified_gfk_related_manager(self, bulk=True):
        Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True, favorite_thing=self.b1)
        droopy = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False, favorite_thing=self.b1)

        # The fun manager DOESN'T remove boring people.
        self.b1.favorite_things(manager='fun_people').remove(droopy, bulk=bulk)
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

        # The boring manager DOES remove boring people.
        self.b1.favorite_things(manager='boring_people').remove(droopy, bulk=bulk)
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='boring_people').all(), [
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        droopy.favorite_thing = self.b1
        droopy.save()

        # The fun manager ONLY clears fun people.
        self.b1.favorite_things(manager='fun_people').clear(bulk=bulk)
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.favorite_things(manager='fun_people').all(), [
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_slow_removal_through_specified_gfk_related_manager(self):
        self.test_removal_through_specified_gfk_related_manager(bulk=False)

    def test_removal_through_default_m2m_related_manager(self):
        bugs = FunPerson.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        self.b1.fun_authors.add(bugs)
        droopy = FunPerson.objects.create(first_name="Droopy", last_name="Dog", fun=False)
        self.b1.fun_authors.add(droopy)

        self.b1.fun_authors.remove(droopy)
        self.assertQuerysetEqual(
            self.b1.fun_authors.through._default_manager.all(), [
                "Bugs",
                "Droopy",
            ],
            lambda c: c.funperson.first_name,
            ordered=False,
        )

        self.b1.fun_authors.remove(bugs)
        self.assertQuerysetEqual(
            self.b1.fun_authors.through._default_manager.all(), [
                "Droopy",
            ],
            lambda c: c.funperson.first_name,
            ordered=False,
        )
        self.b1.fun_authors.add(bugs)

        self.b1.fun_authors.clear()
        self.assertQuerysetEqual(
            self.b1.fun_authors.through._default_manager.all(), [
                "Droopy",
            ],
            lambda c: c.funperson.first_name,
            ordered=False,
        )

    def test_removal_through_specified_m2m_related_manager(self):
        bugs = Person.objects.create(first_name="Bugs", last_name="Bunny", fun=True)
        self.b1.authors.add(bugs)
        droopy = Person.objects.create(first_name="Droopy", last_name="Dog", fun=False)
        self.b1.authors.add(droopy)

        # The fun manager DOESN'T remove boring people.
        self.b1.authors(manager='fun_people').remove(droopy)
        self.assertQuerysetEqual(
            self.b1.authors(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )

        # The boring manager DOES remove boring people.
        self.b1.authors(manager='boring_people').remove(droopy)
        self.assertQuerysetEqual(
            self.b1.authors(manager='boring_people').all(), [
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.b1.authors.add(droopy)

        # The fun manager ONLY clears fun people.
        self.b1.authors(manager='fun_people').clear()
        self.assertQuerysetEqual(
            self.b1.authors(manager='boring_people').all(), [
                "Droopy",
            ],
            lambda c: c.first_name,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.b1.authors(manager='fun_people').all(), [
            ],
            lambda c: c.first_name,
            ordered=False,
        )

    def test_deconstruct_default(self):
        mgr = models.Manager()
        as_manager, mgr_path, qs_path, args, kwargs = mgr.deconstruct()
        self.assertFalse(as_manager)
        self.assertEqual(mgr_path, 'django.db.models.manager.Manager')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {})

    def test_deconstruct_as_manager(self):
        mgr = CustomQuerySet.as_manager()
        as_manager, mgr_path, qs_path, args, kwargs = mgr.deconstruct()
        self.assertTrue(as_manager)
        self.assertEqual(qs_path, 'custom_managers.models.CustomQuerySet')

    def test_deconstruct_from_queryset(self):
        mgr = DeconstructibleCustomManager('a', 'b')
        as_manager, mgr_path, qs_path, args, kwargs = mgr.deconstruct()
        self.assertFalse(as_manager)
        self.assertEqual(mgr_path, 'custom_managers.models.DeconstructibleCustomManager')
        self.assertEqual(args, ('a', 'b',))
        self.assertEqual(kwargs, {})

        mgr = DeconstructibleCustomManager('x', 'y', c=3, d=4)
        as_manager, mgr_path, qs_path, args, kwargs = mgr.deconstruct()
        self.assertFalse(as_manager)
        self.assertEqual(mgr_path, 'custom_managers.models.DeconstructibleCustomManager')
        self.assertEqual(args, ('x', 'y',))
        self.assertEqual(kwargs, {'c': 3, 'd': 4})

    def test_deconstruct_from_queryset_failing(self):
        mgr = CustomManager('arg')
        msg = ("Could not find manager BaseCustomManagerFromCustomQuerySet in "
               "django.db.models.manager.\n"
               "Please note that you need to inherit from managers you "
               "dynamically generated with 'from_queryset()'.")
        with self.assertRaisesMessage(ValueError, msg):
            mgr.deconstruct()

    def test_abstract_model_with_custom_manager_name(self):
        """
        A custom manager may be defined on an abstract model.
        It will be inherited by the abstract model's children.
        """
        PersonFromAbstract.abstract_persons.create(objects='Test')
        self.assertQuerysetEqual(
            PersonFromAbstract.abstract_persons.all(), ["Test"],
            lambda c: c.objects,
        )


class TestCars(TestCase):

    def test_managers(self):
        # Each model class gets a "_default_manager" attribute, which is a
        # reference to the first manager defined in the class.
        Car.cars.create(name="Corvette", mileage=21, top_speed=180)
        Car.cars.create(name="Neon", mileage=31, top_speed=100)

        self.assertQuerysetEqual(
            Car._default_manager.order_by("name"), [
                "Corvette",
                "Neon",
            ],
            lambda c: c.name
        )
        self.assertQuerysetEqual(
            Car.cars.order_by("name"), [
                "Corvette",
                "Neon",
            ],
            lambda c: c.name
        )
        # alternate manager
        self.assertQuerysetEqual(
            Car.fast_cars.all(), [
                "Corvette",
            ],
            lambda c: c.name
        )
        # explicit default manager
        self.assertQuerysetEqual(
            FastCarAsDefault.cars.order_by("name"), [
                "Corvette",
                "Neon",
            ],
            lambda c: c.name
        )
        self.assertQuerysetEqual(
            FastCarAsDefault._default_manager.all(), [
                "Corvette",
            ],
            lambda c: c.name
        )
        # explicit base manager
        self.assertQuerysetEqual(
            FastCarAsBase.cars.order_by("name"), [
                "Corvette",
                "Neon",
            ],
            lambda c: c.name
        )
        self.assertQuerysetEqual(
            FastCarAsBase._base_manager.all(), [
                "Corvette",
            ],
            lambda c: c.name
        )


class CustomManagersRegressTestCase(TestCase):
    def test_filtered_default_manager(self):
        """Even though the default manager filters out some records,
        we must still be able to save (particularly, save by updating
        existing records) those filtered instances. This is a
        regression test for #8990, #9527"""
        related = RelatedModel.objects.create(name="xyzzy")
        obj = RestrictedModel.objects.create(name="hidden", related=related)
        obj.name = "still hidden"
        obj.save()

        # If the hidden object wasn't seen during the save process,
        # there would now be two objects in the database.
        self.assertEqual(RestrictedModel.plain_manager.count(), 1)

    def test_delete_related_on_filtered_manager(self):
        """Deleting related objects should also not be distracted by a
        restricted manager on the related object. This is a regression
        test for #2698."""
        related = RelatedModel.objects.create(name="xyzzy")

        for name, public in (('one', True), ('two', False), ('three', False)):
            RestrictedModel.objects.create(name=name, is_public=public, related=related)

        obj = RelatedModel.objects.get(name="xyzzy")
        obj.delete()

        # All of the RestrictedModel instances should have been
        # deleted, since they *all* pointed to the RelatedModel. If
        # the default manager is used, only the public one will be
        # deleted.
        self.assertEqual(len(RestrictedModel.plain_manager.all()), 0)

    def test_delete_one_to_one_manager(self):
        # The same test case as the last one, but for one-to-one
        # models, which are implemented slightly different internally,
        # so it's a different code path.
        obj = RelatedModel.objects.create(name="xyzzy")
        OneToOneRestrictedModel.objects.create(name="foo", is_public=False, related=obj)
        obj = RelatedModel.objects.get(name="xyzzy")
        obj.delete()
        self.assertEqual(len(OneToOneRestrictedModel.plain_manager.all()), 0)

    def test_queryset_with_custom_init(self):
        """
        BaseManager.get_queryset() should use kwargs rather than args to allow
        custom kwargs (#24911).
        """
        qs_custom = Person.custom_init_queryset_manager.all()
        qs_default = Person.objects.all()
        self.assertQuerysetEqual(qs_custom, qs_default)
