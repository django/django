from __future__ import unicode_literals

from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from .models import (
    Bar, Director, Favorites, HiddenPointer, ManualPrimaryKey, MultiModel,
    Place, Pointer, RelatedModel, Restaurant, School, Target, UndergroundBar,
    Waiter,
)


class OneToOneTests(TestCase):

    def setUp(self):
        self.p1 = Place.objects.create(name='Demon Dogs', address='944 W. Fullerton')
        self.p2 = Place.objects.create(name='Ace Hardware', address='1013 N. Ashland')
        self.r1 = Restaurant.objects.create(place=self.p1, serves_hot_dogs=True, serves_pizza=False)
        self.b1 = Bar.objects.create(place=self.p1, serves_cocktails=False)

    def test_getter(self):
        # A Restaurant can access its place.
        self.assertEqual(repr(self.r1.place), '<Place: Demon Dogs the place>')
        # A Place can access its restaurant, if available.
        self.assertEqual(repr(self.p1.restaurant), '<Restaurant: Demon Dogs the restaurant>')
        # p2 doesn't have an associated restaurant.
        with self.assertRaisesMessage(Restaurant.DoesNotExist, 'Place has no restaurant'):
            self.p2.restaurant
        # The exception raised on attribute access when a related object
        # doesn't exist should be an instance of a subclass of `AttributeError`
        # refs #21563
        self.assertFalse(hasattr(self.p2, 'restaurant'))

    def test_setter(self):
        # Set the place using assignment notation. Because place is the primary
        # key on Restaurant, the save will create a new restaurant
        self.r1.place = self.p2
        self.r1.save()
        self.assertEqual(repr(self.p2.restaurant), '<Restaurant: Ace Hardware the restaurant>')
        self.assertEqual(repr(self.r1.place), '<Place: Ace Hardware the place>')
        self.assertEqual(self.p2.pk, self.r1.pk)
        # Set the place back again, using assignment in the reverse direction.
        self.p1.restaurant = self.r1
        self.assertEqual(repr(self.p1.restaurant), '<Restaurant: Demon Dogs the restaurant>')
        r = Restaurant.objects.get(pk=self.p1.id)
        self.assertEqual(repr(r.place), '<Place: Demon Dogs the place>')

    def test_manager_all(self):
        # Restaurant.objects.all() just returns the Restaurants, not the Places.
        self.assertQuerysetEqual(Restaurant.objects.all(), [
            '<Restaurant: Demon Dogs the restaurant>',
        ])
        # Place.objects.all() returns all Places, regardless of whether they
        # have Restaurants.
        self.assertQuerysetEqual(Place.objects.order_by('name'), [
            '<Place: Ace Hardware the place>',
            '<Place: Demon Dogs the place>',
        ])

    def test_manager_get(self):
        def assert_get_restaurant(**params):
            self.assertEqual(repr(Restaurant.objects.get(**params)),
                             '<Restaurant: Demon Dogs the restaurant>')
        assert_get_restaurant(place__id__exact=self.p1.pk)
        assert_get_restaurant(place__id=self.p1.pk)
        assert_get_restaurant(place__exact=self.p1.pk)
        assert_get_restaurant(place__exact=self.p1)
        assert_get_restaurant(place=self.p1.pk)
        assert_get_restaurant(place=self.p1)
        assert_get_restaurant(pk=self.p1.pk)
        assert_get_restaurant(place__pk__exact=self.p1.pk)
        assert_get_restaurant(place__pk=self.p1.pk)
        assert_get_restaurant(place__name__startswith="Demon")

        def assert_get_place(**params):
            self.assertEqual(repr(Place.objects.get(**params)),
                             '<Place: Demon Dogs the place>')
        assert_get_place(restaurant__place__exact=self.p1.pk)
        assert_get_place(restaurant__place__exact=self.p1)
        assert_get_place(restaurant__place__pk=self.p1.pk)
        assert_get_place(restaurant__exact=self.p1.pk)
        assert_get_place(restaurant__exact=self.r1)
        assert_get_place(restaurant__pk=self.p1.pk)
        assert_get_place(restaurant=self.p1.pk)
        assert_get_place(restaurant=self.r1)
        assert_get_place(id__exact=self.p1.pk)
        assert_get_place(pk=self.p1.pk)

    def test_foreign_key(self):
        # Add a Waiter to the Restaurant.
        w = self.r1.waiter_set.create(name='Joe')
        self.assertEqual(repr(w), '<Waiter: Joe the waiter at Demon Dogs the restaurant>')

        # Query the waiters
        def assert_filter_waiters(**params):
            self.assertQuerysetEqual(Waiter.objects.filter(**params), [
                '<Waiter: Joe the waiter at Demon Dogs the restaurant>'
            ])
        assert_filter_waiters(restaurant__place__exact=self.p1.pk)
        assert_filter_waiters(restaurant__place__exact=self.p1)
        assert_filter_waiters(restaurant__place__pk=self.p1.pk)
        assert_filter_waiters(restaurant__exact=self.r1.pk)
        assert_filter_waiters(restaurant__exact=self.r1)
        assert_filter_waiters(restaurant__pk=self.r1.pk)
        assert_filter_waiters(restaurant=self.r1.pk)
        assert_filter_waiters(restaurant=self.r1)
        assert_filter_waiters(id__exact=w.pk)
        assert_filter_waiters(pk=w.pk)
        # Delete the restaurant; the waiter should also be removed
        r = Restaurant.objects.get(pk=self.r1.pk)
        r.delete()
        self.assertEqual(Waiter.objects.count(), 0)

    def test_multiple_o2o(self):
        # One-to-one fields still work if you create your own primary key
        o1 = ManualPrimaryKey(primary_key="abc123", name="primary")
        o1.save()
        o2 = RelatedModel(link=o1, name="secondary")
        o2.save()

        # You can have multiple one-to-one fields on a model, too.
        x1 = MultiModel(link1=self.p1, link2=o1, name="x1")
        x1.save()
        self.assertEqual(repr(o1.multimodel), '<MultiModel: Multimodel x1>')
        # This will fail because each one-to-one field must be unique (and
        # link2=o1 was used for x1, above).
        mm = MultiModel(link1=self.p2, link2=o1, name="x1")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                mm.save()

    def test_unsaved_object(self):
        """
        #10811 -- Assigning an unsaved object to a OneToOneField
        should raise an exception.
        """
        place = Place(name='User', address='London')
        msg = "save() prohibited to prevent data loss due to unsaved related object 'place'."
        with self.assertRaisesMessage(ValueError, msg):
            Restaurant.objects.create(place=place, serves_hot_dogs=True, serves_pizza=False)

    def test_reverse_relationship_cache_cascade(self):
        """
        Regression test for #9023: accessing the reverse relationship shouldn't
        result in a cascading delete().
        """
        bar = UndergroundBar.objects.create(place=self.p1, serves_cocktails=False)

        # The bug in #9023: if you access the one-to-one relation *before*
        # setting to None and deleting, the cascade happens anyway.
        self.p1.undergroundbar
        bar.place.name = 'foo'
        bar.place = None
        bar.save()
        self.p1.delete()

        self.assertEqual(Place.objects.all().count(), 1)
        self.assertEqual(UndergroundBar.objects.all().count(), 1)

    def test_create_models_m2m(self):
        """
        Regression test for #1064 and #1506

        Check that we create models via the m2m relation if the remote model
        has a OneToOneField.
        """
        f = Favorites(name='Fred')
        f.save()
        f.restaurants = [self.r1]
        self.assertQuerysetEqual(
            f.restaurants.all(),
            ['<Restaurant: Demon Dogs the restaurant>']
        )

    def test_reverse_object_cache(self):
        """
        Regression test for #7173

        Check that the name of the cache for the reverse object is correct.
        """
        self.assertEqual(self.p1.restaurant, self.r1)
        self.assertEqual(self.p1.bar, self.b1)

    def test_related_object_cache(self):
        """ Regression test for #6886 (the related-object cache) """

        # Look up the objects again so that we get "fresh" objects
        p = Place.objects.get(name="Demon Dogs")
        r = p.restaurant

        # Accessing the related object again returns the exactly same object
        self.assertIs(p.restaurant, r)

        # But if we kill the cache, we get a new object
        del p._restaurant_cache
        self.assertIsNot(p.restaurant, r)

        # Reassigning the Restaurant object results in an immediate cache update
        # We can't use a new Restaurant because that'll violate one-to-one, but
        # with a new *instance* the is test below will fail if #6886 regresses.
        r2 = Restaurant.objects.get(pk=r.pk)
        p.restaurant = r2
        self.assertIs(p.restaurant, r2)

        # Assigning None succeeds if field is null=True.
        ug_bar = UndergroundBar.objects.create(place=p, serves_cocktails=False)
        ug_bar.place = None
        self.assertIsNone(ug_bar.place)

        # Assigning None fails: Place.restaurant is null=False
        self.assertRaises(ValueError, setattr, p, 'restaurant', None)

        # You also can't assign an object of the wrong type here
        self.assertRaises(ValueError, setattr, p, 'restaurant', p)

        # Creation using keyword argument should cache the related object.
        p = Place.objects.get(name="Demon Dogs")
        r = Restaurant(place=p)
        self.assertIs(r.place, p)

        # Creation using keyword argument and unsaved related instance (#8070).
        p = Place()
        r = Restaurant(place=p)
        self.assertTrue(r.place is p)

        # Creation using attname keyword argument and an id will cause the related
        # object to be fetched.
        p = Place.objects.get(name="Demon Dogs")
        r = Restaurant(place_id=p.id)
        self.assertIsNot(r.place, p)
        self.assertEqual(r.place, p)

    def test_filter_one_to_one_relations(self):
        """
        Regression test for #9968

        filtering reverse one-to-one relations with primary_key=True was
        misbehaving. We test both (primary_key=True & False) cases here to
        prevent any reappearance of the problem.
        """
        Target.objects.create()

        self.assertQuerysetEqual(
            Target.objects.filter(pointer=None),
            ['<Target: Target object>']
        )
        self.assertQuerysetEqual(
            Target.objects.exclude(pointer=None),
            []
        )
        self.assertQuerysetEqual(
            Target.objects.filter(second_pointer=None),
            ['<Target: Target object>']
        )
        self.assertQuerysetEqual(
            Target.objects.exclude(second_pointer=None),
            []
        )

    def test_o2o_primary_key_delete(self):
        t = Target.objects.create(name='name')
        Pointer.objects.create(other=t)
        Pointer.objects.filter(other__name='name').delete()

    def test_reverse_object_does_not_exist_cache(self):
        """
        Regression for #13839 and #17439.

        DoesNotExist on a reverse one-to-one relation is cached.
        """
        p = Place(name='Zombie Cats', address='Not sure')
        p.save()
        with self.assertNumQueries(1):
            with self.assertRaises(Restaurant.DoesNotExist):
                p.restaurant
        with self.assertNumQueries(0):
            with self.assertRaises(Restaurant.DoesNotExist):
                p.restaurant

    def test_reverse_object_cached_when_related_is_accessed(self):
        """
        Regression for #13839 and #17439.

        The target of a one-to-one relation is cached
        when the origin is accessed through the reverse relation.
        """
        # Use a fresh object without caches
        r = Restaurant.objects.get(pk=self.r1.pk)
        p = r.place
        with self.assertNumQueries(0):
            self.assertEqual(p.restaurant, r)

    def test_related_object_cached_when_reverse_is_accessed(self):
        """
        Regression for #13839 and #17439.

        The origin of a one-to-one relation is cached
        when the target is accessed through the reverse relation.
        """
        # Use a fresh object without caches
        p = Place.objects.get(pk=self.p1.pk)
        r = p.restaurant
        with self.assertNumQueries(0):
            self.assertEqual(r.place, p)

    def test_reverse_object_cached_when_related_is_set(self):
        """
        Regression for #13839 and #17439.

        The target of a one-to-one relation is always cached.
        """
        p = Place(name='Zombie Cats', address='Not sure')
        p.save()
        self.r1.place = p
        self.r1.save()
        with self.assertNumQueries(0):
            self.assertEqual(p.restaurant, self.r1)

    def test_reverse_object_cached_when_related_is_unset(self):
        """
        Regression for #13839 and #17439.

        The target of a one-to-one relation is always cached.
        """
        b = UndergroundBar(place=self.p1, serves_cocktails=True)
        b.save()
        with self.assertNumQueries(0):
            self.assertEqual(self.p1.undergroundbar, b)
        b.place = None
        b.save()
        with self.assertNumQueries(0):
            with self.assertRaises(UndergroundBar.DoesNotExist):
                self.p1.undergroundbar

    def test_get_reverse_on_unsaved_object(self):
        """
        Regression for #18153 and #19089.

        Accessing the reverse relation on an unsaved object
        always raises an exception.
        """
        p = Place()

        # When there's no instance of the origin of the one-to-one
        with self.assertNumQueries(0):
            with self.assertRaises(UndergroundBar.DoesNotExist):
                p.undergroundbar

        UndergroundBar.objects.create()

        # When there's one instance of the origin
        # (p.undergroundbar used to return that instance)
        with self.assertNumQueries(0):
            with self.assertRaises(UndergroundBar.DoesNotExist):
                p.undergroundbar

        # Several instances of the origin are only possible if database allows
        # inserting multiple NULL rows for a unique constraint
        if connection.features.supports_nullable_unique_constraints:
            UndergroundBar.objects.create()

            # When there are several instances of the origin
            with self.assertNumQueries(0):
                with self.assertRaises(UndergroundBar.DoesNotExist):
                    p.undergroundbar

    def test_set_reverse_on_unsaved_object(self):
        """
        Writing to the reverse relation on an unsaved object
        is impossible too.
        """
        p = Place()
        b = UndergroundBar.objects.create()

        # Assigning a reverse relation on an unsaved object is allowed.
        p.undergroundbar = b

        # However saving the object is not allowed.
        msg = "save() prohibited to prevent data loss due to unsaved related object 'place'."
        with self.assertNumQueries(0):
            with self.assertRaisesMessage(ValueError, msg):
                b.save()

    def test_nullable_o2o_delete(self):
        u = UndergroundBar.objects.create(place=self.p1)
        u.place_id = None
        u.save()
        self.p1.delete()
        self.assertTrue(UndergroundBar.objects.filter(pk=u.pk).exists())
        self.assertIsNone(UndergroundBar.objects.get(pk=u.pk).place)

    def test_hidden_accessor(self):
        """
        When a '+' ending related name is specified no reverse accessor should
        be added to the related model.
        """
        self.assertFalse(
            hasattr(Target, HiddenPointer._meta.get_field('target').rel.get_accessor_name())
        )

    def test_related_object(self):
        public_school = School.objects.create(is_public=True)
        public_director = Director.objects.create(school=public_school, is_temp=False)

        private_school = School.objects.create(is_public=False)
        private_director = Director.objects.create(school=private_school, is_temp=True)

        # Only one school is available via all() due to the custom default manager.
        self.assertQuerysetEqual(
            School.objects.all(),
            ["<School: School object>"]
        )

        # Only one director is available via all() due to the custom default manager.
        self.assertQuerysetEqual(
            Director.objects.all(),
            ["<Director: Director object>"]
        )

        self.assertEqual(public_director.school, public_school)
        self.assertEqual(public_school.director, public_director)

        # Make sure the base manager is used so that the related objects
        # is still accessible even if the default manager doesn't normally
        # allow it.
        self.assertEqual(private_director.school, private_school)

        # Make sure the base manager is used so that an student can still access
        # its related school even if the default manager doesn't normally
        # allow it.
        self.assertEqual(private_school.director, private_director)

        # If the manager is marked "use_for_related_fields", it'll get used instead
        # of the "bare" queryset. Usually you'd define this as a property on the class,
        # but this approximates that in a way that's easier in tests.
        School.objects.use_for_related_fields = True
        try:
            private_director = Director._base_manager.get(pk=private_director.pk)
            self.assertRaises(School.DoesNotExist, lambda: private_director.school)
        finally:
            School.objects.use_for_related_fields = False

        Director.objects.use_for_related_fields = True
        try:
            private_school = School._base_manager.get(pk=private_school.pk)
            self.assertRaises(Director.DoesNotExist, lambda: private_school.director)
        finally:
            Director.objects.use_for_related_fields = False

    def test_hasattr_related_object(self):
        # The exception raised on attribute access when a related object
        # doesn't exist should be an instance of a subclass of `AttributeError`
        # refs #21563
        self.assertFalse(hasattr(Director(), 'director'))
        self.assertFalse(hasattr(School(), 'school'))

    def test_update_one_to_one_pk(self):
        p1 = Place.objects.create()
        p2 = Place.objects.create()
        r1 = Restaurant.objects.create(place=p1)
        r2 = Restaurant.objects.create(place=p2)
        w = Waiter.objects.create(restaurant=r1)

        Waiter.objects.update(restaurant=r2)
        w.refresh_from_db()
        self.assertEqual(w.restaurant, r2)
