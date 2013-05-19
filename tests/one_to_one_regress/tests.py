from __future__ import absolute_import

from django.test import TestCase

from .models import Place, Restaurant, Bar, Favorites, Target, UndergroundBar


class OneToOneRegressionTests(TestCase):

    def setUp(self):
        self.p1 = Place(name='Demon Dogs', address='944 W. Fullerton')
        self.p1.save()
        self.r1 = Restaurant(place=self.p1, serves_hot_dogs=True, serves_pizza=False)
        self.r1.save()
        self.b1 = Bar(place=self.p1, serves_cocktails=False)
        self.b1.save()

    def test_reverse_relationship_cache_cascade(self):
        """
        Regression test for #9023: accessing the reverse relationship shouldn't
        result in a cascading delete().
        """
        bar = UndergroundBar.objects.create(place=self.p1, serves_cocktails=False)

        # The bug in #9023: if you access the one-to-one relation *before*
        # setting to None and deleting, the cascade happens anyway.
        self.p1.undergroundbar
        bar.place.name='foo'
        bar.place = None
        bar.save()
        self.p1.delete()

        self.assertEqual(Place.objects.all().count(), 0)
        self.assertEqual(UndergroundBar.objects.all().count(), 1)

    def test_create_models_m2m(self):
        """
        Regression test for #1064 and #1506

        Check that we create models via the m2m relation if the remote model
        has a OneToOneField.
        """
        f = Favorites(name = 'Fred')
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
        self.assertTrue(p.restaurant is r)

        # But if we kill the cache, we get a new object
        del p._restaurant_cache
        self.assertFalse(p.restaurant is r)

        # Reassigning the Restaurant object results in an immediate cache update
        # We can't use a new Restaurant because that'll violate one-to-one, but
        # with a new *instance* the is test below will fail if #6886 regresses.
        r2 = Restaurant.objects.get(pk=r.pk)
        p.restaurant = r2
        self.assertTrue(p.restaurant is r2)

        # Assigning None succeeds if field is null=True.
        ug_bar = UndergroundBar.objects.create(place=p, serves_cocktails=False)
        ug_bar.place = None
        self.assertTrue(ug_bar.place is None)

        # Assigning None fails: Place.restaurant is null=False
        self.assertRaises(ValueError, setattr, p, 'restaurant', None)

        # You also can't assign an object of the wrong type here
        self.assertRaises(ValueError, setattr, p, 'restaurant', p)

        # Creation using keyword argument should cache the related object.
        p = Place.objects.get(name="Demon Dogs")
        r = Restaurant(place=p)
        self.assertTrue(r.place is p)

        # Creation using keyword argument and unsaved related instance (#8070).
        p = Place()
        r = Restaurant(place=p)
        self.assertTrue(r.place is p)

        # Creation using attname keyword argument and an id will cause the related
        # object to be fetched.
        p = Place.objects.get(name="Demon Dogs")
        r = Restaurant(place_id=p.id)
        self.assertFalse(r.place is p)
        self.assertEqual(r.place, p)

    def test_filter_one_to_one_relations(self):
        """
        Regression test for #9968

        filtering reverse one-to-one relations with primary_key=True was
        misbehaving. We test both (primary_key=True & False) cases here to
        prevent any reappearance of the problem.
        """
        t = Target.objects.create()

        self.assertQuerysetEqual(
                Target.objects.filter(pointer=None),
                ['<Target: Target object>']
        )
        self.assertQuerysetEqual(
                Target.objects.exclude(pointer=None),
                []
        )
        self.assertQuerysetEqual(
                Target.objects.filter(pointer2=None),
                ['<Target: Target object>']
        )
        self.assertQuerysetEqual(
                Target.objects.exclude(pointer2=None),
                []
        )

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
        with self.assertNumQueries(0):
            with self.assertRaises(ValueError):
                p.undergroundbar = b
