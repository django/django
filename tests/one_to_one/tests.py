from unittest.mock import patch

from django.core.exceptions import FieldFetchBlocked
from django.db import IntegrityError, connection, transaction
from django.db.models import FETCH_PEERS, RAISE, QuerySet
from django.test import TestCase

from .models import (
    Bar,
    Branch,
    Director,
    Favorites,
    HiddenPointer,
    ManualPrimaryKey,
    MultiModel,
    Place,
    PlaceProxyPointer,
    Pointer,
    ProxyPlace,
    RelatedModel,
    Restaurant,
    School,
    Target,
    ToFieldPointer,
    UndergroundBar,
    Waiter,
)


class OneToOneTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = Place.objects.create(name="Demon Dogs", address="944 W. Fullerton")
        cls.p2 = Place.objects.create(name="Ace Hardware", address="1013 N. Ashland")
        cls.r1 = Restaurant.objects.create(
            place=cls.p1, serves_hot_dogs=True, serves_pizza=False
        )
        cls.b1 = Bar.objects.create(place=cls.p1, serves_cocktails=False)

    def test_getter(self):
        # A Restaurant can access its place.
        self.assertEqual(repr(self.r1.place), "<Place: Demon Dogs the place>")
        # A Place can access its restaurant, if available.
        self.assertEqual(
            repr(self.p1.restaurant), "<Restaurant: Demon Dogs the restaurant>"
        )
        # p2 doesn't have an associated restaurant.
        with self.assertRaisesMessage(
            Restaurant.DoesNotExist, "Place has no restaurant"
        ):
            self.p2.restaurant
        # The exception raised on attribute access when a related object
        # doesn't exist should be an instance of a subclass of `AttributeError`
        # refs #21563
        self.assertFalse(hasattr(self.p2, "restaurant"))

    def test_setter(self):
        # Set the place using assignment notation. Because place is the primary
        # key on Restaurant, the save will create a new restaurant
        self.r1.place = self.p2
        self.r1.save()
        self.assertEqual(
            repr(self.p2.restaurant), "<Restaurant: Ace Hardware the restaurant>"
        )
        self.assertEqual(repr(self.r1.place), "<Place: Ace Hardware the place>")
        self.assertEqual(self.p2.pk, self.r1.pk)
        # Set the place back again, using assignment in the reverse direction.
        self.p1.restaurant = self.r1
        self.assertEqual(
            repr(self.p1.restaurant), "<Restaurant: Demon Dogs the restaurant>"
        )
        r = Restaurant.objects.get(pk=self.p1.id)
        self.assertEqual(repr(r.place), "<Place: Demon Dogs the place>")

    def test_manager_all(self):
        # Restaurant.objects.all() just returns the Restaurants, not the
        # Places.
        self.assertSequenceEqual(Restaurant.objects.all(), [self.r1])
        # Place.objects.all() returns all Places, regardless of whether they
        # have Restaurants.
        self.assertSequenceEqual(Place.objects.order_by("name"), [self.p2, self.p1])

    def test_manager_get(self):
        def assert_get_restaurant(**params):
            self.assertEqual(
                repr(Restaurant.objects.get(**params)),
                "<Restaurant: Demon Dogs the restaurant>",
            )

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
            self.assertEqual(
                repr(Place.objects.get(**params)), "<Place: Demon Dogs the place>"
            )

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
        w = self.r1.waiter_set.create(name="Joe")
        self.assertEqual(
            repr(w), "<Waiter: Joe the waiter at Demon Dogs the restaurant>"
        )

        # Query the waiters
        def assert_filter_waiters(**params):
            self.assertSequenceEqual(Waiter.objects.filter(**params), [w])

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
        self.assertEqual(repr(o1.multimodel), "<MultiModel: Multimodel x1>")
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
        place = Place(name="User", address="London")
        with self.assertRaises(Restaurant.DoesNotExist):
            place.restaurant
        msg = (
            "save() prohibited to prevent data loss due to unsaved related object "
            "'place'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Restaurant.objects.create(
                place=place, serves_hot_dogs=True, serves_pizza=False
            )
        # place should not cache restaurant
        with self.assertRaises(Restaurant.DoesNotExist):
            place.restaurant

    def test_reverse_relationship_cache_cascade(self):
        """
        Regression test for #9023: accessing the reverse relationship shouldn't
        result in a cascading delete().
        """
        bar = UndergroundBar.objects.create(place=self.p1, serves_cocktails=False)

        # The bug in #9023: if you access the one-to-one relation *before*
        # setting to None and deleting, the cascade happens anyway.
        self.p1.undergroundbar
        bar.place.name = "foo"
        bar.place = None
        bar.save()
        self.p1.delete()

        self.assertEqual(Place.objects.count(), 1)
        self.assertEqual(UndergroundBar.objects.count(), 1)

    def test_create_models_m2m(self):
        """
        Models are created via the m2m relation if the remote model has a
        OneToOneField (#1064, #1506).
        """
        f = Favorites(name="Fred")
        f.save()
        f.restaurants.set([self.r1])
        self.assertSequenceEqual(f.restaurants.all(), [self.r1])

    def test_reverse_object_cache(self):
        """
        The name of the cache for the reverse object is correct (#7173).
        """
        self.assertEqual(self.p1.restaurant, self.r1)
        self.assertEqual(self.p1.bar, self.b1)

    def test_assign_none_reverse_relation(self):
        p = Place.objects.get(name="Demon Dogs")
        # Assigning None succeeds if field is null=True.
        ug_bar = UndergroundBar.objects.create(place=p, serves_cocktails=False)
        p.undergroundbar = None
        self.assertIsNone(ug_bar.place)
        ug_bar.save()
        ug_bar.refresh_from_db()
        self.assertIsNone(ug_bar.place)

    def test_assign_none_null_reverse_relation(self):
        p = Place.objects.get(name="Demon Dogs")
        # Assigning None doesn't throw AttributeError if there isn't a related
        # UndergroundBar.
        p.undergroundbar = None

    def test_assign_none_to_null_cached_reverse_relation(self):
        p = Place.objects.get(name="Demon Dogs")
        # Prime the relation's cache with a value of None.
        with self.assertRaises(Place.undergroundbar.RelatedObjectDoesNotExist):
            getattr(p, "undergroundbar")
        # Assigning None works if there isn't a related UndergroundBar and the
        # reverse cache has a value of None.
        p.undergroundbar = None

    def test_assign_o2o_id_value(self):
        b = UndergroundBar.objects.create(place=self.p1)
        b.place_id = self.p2.pk
        b.save()
        self.assertEqual(b.place_id, self.p2.pk)
        self.assertFalse(UndergroundBar.place.is_cached(b))
        self.assertEqual(b.place, self.p2)
        self.assertTrue(UndergroundBar.place.is_cached(b))
        # Reassigning the same value doesn't clear a cached instance.
        b.place_id = self.p2.pk
        self.assertTrue(UndergroundBar.place.is_cached(b))

    def test_assign_o2o_id_none(self):
        b = UndergroundBar.objects.create(place=self.p1)
        b.place_id = None
        b.save()
        self.assertIsNone(b.place_id)
        self.assertFalse(UndergroundBar.place.is_cached(b))
        self.assertIsNone(b.place)
        self.assertTrue(UndergroundBar.place.is_cached(b))

    def test_related_object_cache(self):
        """Regression test for #6886 (the related-object cache)"""

        # Look up the objects again so that we get "fresh" objects
        p = Place.objects.get(name="Demon Dogs")
        r = p.restaurant

        # Accessing the related object again returns the exactly same object
        self.assertIs(p.restaurant, r)

        # But if we kill the cache, we get a new object
        del p._state.fields_cache["restaurant"]
        self.assertIsNot(p.restaurant, r)

        # Reassigning the Restaurant object results in an immediate cache
        # update We can't use a new Restaurant because that'll violate
        # one-to-one, but with a new *instance* the is test below will fail if
        # #6886 regresses.
        r2 = Restaurant.objects.get(pk=r.pk)
        p.restaurant = r2
        self.assertIs(p.restaurant, r2)

        # Assigning None succeeds if field is null=True.
        ug_bar = UndergroundBar.objects.create(place=p, serves_cocktails=False)
        ug_bar.place = None
        self.assertIsNone(ug_bar.place)

        # Assigning None will not fail: Place.restaurant is null=False
        setattr(p, "restaurant", None)

        # You also can't assign an object of the wrong type here
        msg = (
            'Cannot assign "<Place: Demon Dogs the place>": '
            '"Place.restaurant" must be a "Restaurant" instance.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            setattr(p, "restaurant", p)

        # Creation using keyword argument should cache the related object.
        p = Place.objects.get(name="Demon Dogs")
        r = Restaurant(place=p)
        self.assertIs(r.place, p)

        # Creation using keyword argument and unsaved related instance (#8070).
        p = Place()
        r = Restaurant(place=p)
        self.assertIs(r.place, p)

        # Creation using attname keyword argument and an id will cause the
        # related object to be fetched.
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
        target = Target.objects.create()
        self.assertSequenceEqual(Target.objects.filter(pointer=None), [target])
        self.assertSequenceEqual(Target.objects.exclude(pointer=None), [])
        self.assertSequenceEqual(Target.objects.filter(second_pointer=None), [target])
        self.assertSequenceEqual(Target.objects.exclude(second_pointer=None), [])

    def test_o2o_primary_key_delete(self):
        t = Target.objects.create(name="name")
        Pointer.objects.create(other=t)
        num_deleted, objs = Pointer.objects.filter(other__name="name").delete()
        self.assertEqual(num_deleted, 1)
        self.assertEqual(objs, {"one_to_one.Pointer": 1})

    def test_save_nullable_o2o_after_parent(self):
        place = Place(name="Rose tattoo")
        bar = UndergroundBar(place=place)
        place.save()
        bar.save()
        bar.refresh_from_db()
        self.assertEqual(bar.place, place)

    def test_reverse_object_does_not_exist_cache(self):
        """
        Regression for #13839 and #17439.

        DoesNotExist on a reverse one-to-one relation is cached.
        """
        p = Place(name="Zombie Cats", address="Not sure")
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
        p = Place(name="Zombie Cats", address="Not sure")
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
        msg = (
            "save() prohibited to prevent data loss due to unsaved related object "
            "'place'."
        )
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
            hasattr(
                Target,
                HiddenPointer._meta.get_field("target").remote_field.accessor_name,
            )
        )

    def test_related_object(self):
        public_school = School.objects.create(is_public=True)
        public_director = Director.objects.create(school=public_school, is_temp=False)

        private_school = School.objects.create(is_public=False)
        private_director = Director.objects.create(school=private_school, is_temp=True)

        # Only one school is available via all() due to the custom default
        # manager.
        self.assertSequenceEqual(School.objects.all(), [public_school])

        # Only one director is available via all() due to the custom default
        # manager.
        self.assertSequenceEqual(Director.objects.all(), [public_director])

        self.assertEqual(public_director.school, public_school)
        self.assertEqual(public_school.director, public_director)

        # Make sure the base manager is used so that the related objects
        # is still accessible even if the default manager doesn't normally
        # allow it.
        self.assertEqual(private_director.school, private_school)

        # Make sure the base manager is used so that an student can still
        # access its related school even if the default manager doesn't
        # normally allow it.
        self.assertEqual(private_school.director, private_director)

        School._meta.base_manager_name = "objects"
        School._meta._expire_cache()
        try:
            private_director = Director._base_manager.get(pk=private_director.pk)
            with self.assertRaises(School.DoesNotExist):
                private_director.school
        finally:
            School._meta.base_manager_name = None
            School._meta._expire_cache()

        Director._meta.base_manager_name = "objects"
        Director._meta._expire_cache()
        try:
            private_school = School._base_manager.get(pk=private_school.pk)
            with self.assertRaises(Director.DoesNotExist):
                private_school.director
        finally:
            Director._meta.base_manager_name = None
            Director._meta._expire_cache()

    def test_create_reverse_o2o_error(self):
        msg = "The following fields do not exist in this model: restaurant"
        with self.assertRaisesMessage(ValueError, msg):
            Place.objects.create(restaurant=self.r1)

    def test_get_or_create_reverse_o2o_error(self):
        msg = "The following fields do not exist in this model: restaurant"
        r2 = Restaurant.objects.create(
            place=self.p2, serves_hot_dogs=True, serves_pizza=False
        )
        with self.assertRaisesMessage(ValueError, msg):
            Place.objects.get_or_create(name="nonexistent", defaults={"restaurant": r2})

    def test_update_or_create_reverse_o2o_error(self):
        msg = "The following fields do not exist in this model: restaurant"
        r2 = Restaurant.objects.create(
            place=self.p2, serves_hot_dogs=True, serves_pizza=False
        )
        with self.assertRaisesMessage(ValueError, msg):
            Place.objects.update_or_create(
                name="nonexistent", defaults={"restaurant": r2}
            )

    def test_hasattr_related_object(self):
        # The exception raised on attribute access when a related object
        # doesn't exist should be an instance of a subclass of `AttributeError`
        # refs #21563
        self.assertFalse(hasattr(Director(), "director"))
        self.assertFalse(hasattr(School(), "school"))

    def test_update_one_to_one_pk(self):
        p1 = Place.objects.create()
        p2 = Place.objects.create()
        r1 = Restaurant.objects.create(place=p1)
        r2 = Restaurant.objects.create(place=p2)
        w = Waiter.objects.create(restaurant=r1)

        Waiter.objects.update(restaurant=r2)
        w.refresh_from_db()
        self.assertEqual(w.restaurant, r2)

    def test_rel_pk_subquery(self):
        r = Restaurant.objects.first()
        q1 = Restaurant.objects.filter(place_id=r.pk)
        # Subquery using primary key and a query against the
        # same model works correctly.
        q2 = Restaurant.objects.filter(place_id__in=q1)
        self.assertSequenceEqual(q2, [r])
        # Subquery using 'pk__in' instead of 'place_id__in' work, too.
        q2 = Restaurant.objects.filter(
            pk__in=Restaurant.objects.filter(place__id=r.place.pk)
        )
        self.assertSequenceEqual(q2, [r])
        q3 = Restaurant.objects.filter(place__in=Place.objects.all())
        self.assertSequenceEqual(q3, [r])
        q4 = Restaurant.objects.filter(place__in=Place.objects.filter(id=r.pk))
        self.assertSequenceEqual(q4, [r])

    def test_rel_pk_exact(self):
        r = Restaurant.objects.first()
        r2 = Restaurant.objects.filter(pk__exact=r).first()
        self.assertEqual(r, r2)

    def test_primary_key_to_field_filter(self):
        target = Target.objects.create(name="foo")
        pointer = ToFieldPointer.objects.create(target=target)
        self.assertSequenceEqual(
            ToFieldPointer.objects.filter(target=target), [pointer]
        )
        self.assertSequenceEqual(
            ToFieldPointer.objects.filter(pk__exact=pointer), [pointer]
        )

    def test_cached_relation_invalidated_on_save(self):
        """
        Model.save() invalidates stale OneToOneField relations after a primary
        key assignment.
        """
        self.assertEqual(self.b1.place, self.p1)  # caches b1.place
        self.b1.place_id = self.p2.pk
        self.b1.save()
        self.assertEqual(self.b1.place, self.p2)

    def test_get_prefetch_querysets_invalid_querysets_length(self):
        places = Place.objects.all()
        msg = (
            "querysets argument of get_prefetch_querysets() should have a length of 1."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Place.bar.get_prefetch_querysets(
                instances=places,
                querysets=[Bar.objects.all(), Bar.objects.all()],
            )

    def test_fetch_mode_fetch_peers_forward(self):
        Restaurant.objects.create(
            place=self.p2, serves_hot_dogs=True, serves_pizza=False
        )
        r1, r2 = Restaurant.objects.fetch_mode(FETCH_PEERS)
        with self.assertNumQueries(1):
            r1.place
        with self.assertNumQueries(0):
            r2.place

    def test_fetch_mode_fetch_peers_reverse(self):
        Restaurant.objects.create(
            place=self.p2, serves_hot_dogs=True, serves_pizza=False
        )
        p1, p2 = Place.objects.fetch_mode(FETCH_PEERS)
        with self.assertNumQueries(1):
            p1.restaurant
        with self.assertNumQueries(0):
            p2.restaurant

    def test_fetch_mode_raise_forward(self):
        r = Restaurant.objects.fetch_mode(RAISE).get(pk=self.r1.pk)
        msg = "Fetching of Restaurant.place blocked."
        with self.assertRaisesMessage(FieldFetchBlocked, msg) as cm:
            r.place
        self.assertIsNone(cm.exception.__cause__)
        self.assertTrue(cm.exception.__suppress_context__)

    def test_fetch_mode_raise_reverse(self):
        p = Place.objects.fetch_mode(RAISE).get(pk=self.p1.pk)
        msg = "Fetching of Place.restaurant blocked."
        with self.assertRaisesMessage(FieldFetchBlocked, msg) as cm:
            p.restaurant
        self.assertIsNone(cm.exception.__cause__)
        self.assertTrue(cm.exception.__suppress_context__)

    def test_fetch_mode_copied_forward_fetching_one(self):
        r1 = Restaurant.objects.fetch_mode(FETCH_PEERS).get(pk=self.r1.pk)
        self.assertEqual(r1._state.fetch_mode, FETCH_PEERS)
        self.assertEqual(
            r1.place._state.fetch_mode,
            FETCH_PEERS,
        )

    def test_fetch_mode_copied_forward_fetching_many(self):
        Restaurant.objects.create(
            place=self.p2, serves_hot_dogs=True, serves_pizza=False
        )
        r1, r2 = Restaurant.objects.fetch_mode(FETCH_PEERS)
        self.assertEqual(r1._state.fetch_mode, FETCH_PEERS)
        self.assertEqual(
            r1.place._state.fetch_mode,
            FETCH_PEERS,
        )

    def test_fetch_mode_copied_reverse_fetching_one(self):
        p1 = Place.objects.fetch_mode(FETCH_PEERS).get(pk=self.p1.pk)
        self.assertEqual(p1._state.fetch_mode, FETCH_PEERS)
        self.assertEqual(
            p1.restaurant._state.fetch_mode,
            FETCH_PEERS,
        )

    def test_fetch_mode_copied_reverse_fetching_many(self):
        Restaurant.objects.create(
            place=self.p2, serves_hot_dogs=True, serves_pizza=False
        )
        p1, p2 = Place.objects.fetch_mode(FETCH_PEERS)
        self.assertEqual(p1._state.fetch_mode, FETCH_PEERS)
        self.assertEqual(
            p1.restaurant._state.fetch_mode,
            FETCH_PEERS,
        )

    def test_get_or_create_race_keeps_reverse_o2o_cache_consistent(self):
        """
        Regression test for #36489.

        Simulate two concurrent Bar.get_or_create(place=...) calls
        racing on the same OneToOneField. The loser of the insert must not
        leave an unsaved instance cached on the reverse side (place.bar
        with pk=None). After get_or_create(), place.bar must resolve to
        the saved row.

        Bar is used (not Restaurant) because Bar.place is not the primary
        key, so bar.pk is genuinely None before save() and the stale-cache
        bug can be observed.
        """
        place = Place.objects.create(name="Race Diner", address="Somewhere")

        # We'll inject a concurrent get_or_create inside the first one by
        # patching QuerySet._extract_model_params
        original = QuerySet._extract_model_params
        triggered = {"done": False}

        def side_effect(self, defaults=None, **kwargs):
            # Only re-enter once, and only for the same place kwarg.
            if not triggered["done"] and kwargs.get("place") == place:
                triggered["done"] = True
                # Use a *fresh* instance of place to emulate a separate thread.
                Bar.objects.get_or_create(place=Place.objects.get(pk=place.pk))
            return original(self, defaults, **kwargs)

        with patch(
            "django.db.models.query.QuerySet._extract_model_params",
            side_effect,
        ):
            bar, created = Bar.objects.get_or_create(place=place)
            self.assertFalse(created)

        # The reverse cache must not contain an unsaved Bar.
        # Accessing place.bar should yield a saved row with a pk,
        # and it should be the same row returned above.
        self.assertIsNotNone(bar.pk)
        self.assertIsNotNone(place.bar.pk)
        self.assertEqual(place.bar.pk, bar.pk)
        self.assertEqual(bar.place_id, place.pk)

    def test_get_or_create_race_does_not_clear_valid_select_related_cache(self):
        place = Place.objects.create(name="Silver Square", address="Somewhere")
        Bar.objects.create(place=place)

        # Prime a valid forward cache via select_related()
        # (we don't clear this path).
        fetched = Bar.objects.select_related("place").get(place=place)

        # Run a no-op get_or_create (no IntegrityError path taken).
        _, created = Bar.objects.get_or_create(place=place)
        self.assertFalse(created)

        # Using the forward cache should not cause a query.
        with self.assertNumQueries(0):
            _ = fetched.place.id

    def test_update_or_create_race_keeps_reverse_o2o_cache_consistent(self):
        """
        Regression test for #36489 (update_or_create path).

        Simulate two concurrent Bar.update_or_create(place=...) calls
        racing on the same OneToOneField. The loser of the insert must not
        leave an unsaved instance cached on the reverse side (place.bar
        with pk=None). After update_or_create(), place.bar must resolve
        to the saved row.
        """
        place = Place.objects.create(name="Update Race Diner", address="Somewhere")

        # Inject a concurrent get_or_create inside the first one by
        # patching QuerySet._extract_model_params.
        original = QuerySet._extract_model_params
        triggered = {"done": False}

        def side_effect(self, defaults=None, **kwargs):
            if not triggered["done"] and kwargs.get("place") == place:
                triggered["done"] = True
                # Use a fresh instance of place to emulate a separate thread.
                Bar.objects.get_or_create(place=Place.objects.get(pk=place.pk))
            return original(self, defaults, **kwargs)

        with patch(
            "django.db.models.query.QuerySet._extract_model_params", side_effect
        ):
            bar, created = Bar.objects.update_or_create(
                place=place,
                defaults={"serves_cocktails": False},
            )
            self.assertFalse(created)

        # The reverse cache must not contain an unsaved Bar.
        # Accessing place.bar should yield a saved row with a pk,
        # and it should be the same row returned above.
        self.assertIsNotNone(bar.pk)
        self.assertIsNotNone(place.bar.pk)
        self.assertEqual(place.bar.pk, bar.pk)
        self.assertEqual(bar.place_id, place.pk)

    def test_update_or_create_race_with_defaults_reverse_o2o_cache_consistent(self):
        """
        Regression test for #36489 (defaults/create_defaults path).

        Simulate two concurrent Bar.update_or_create(place=...) calls
        with non-trivial defaults. The loser of the insert must not leave an
        unsaved instance cached on the reverse side (place.bar with pk=None).
        After update_or_create(), place.bar must resolve to the saved row,
        and the defaults must be consistent with the actual saved object.
        """
        place = Place.objects.create(name="Defaults Diner", address="Anywhere")

        default_context = {"serves_cocktails": True}
        alt_context = {"serves_cocktails": False}

        # Inject a concurrent get_or_create inside the first one.
        original = QuerySet._extract_model_params
        triggered = {"done": False}

        def side_effect(self, defaults=None, **kwargs):
            if not triggered["done"] and kwargs.get("place") == place:
                triggered["done"] = True
                Bar.objects.update_or_create(
                    place=Place.objects.get(pk=place.pk),
                    defaults=alt_context,
                )
            return original(self, defaults, **kwargs)

        with patch(
            "django.db.models.query.QuerySet._extract_model_params", side_effect
        ):
            bar, created = Bar.objects.update_or_create(
                place=place,
                defaults=default_context,
            )
            self.assertFalse(created)

        # The reverse cache must not contain an unsaved Bar.
        self.assertIsNotNone(bar.pk)
        self.assertIsNotNone(place.bar.pk)
        self.assertEqual(place.bar.pk, bar.pk)
        self.assertEqual(bar.place_id, place.pk)

        # Ensure the actual persisted defaults match the winning insert,
        # not some stale in-memory values.
        db_bar = Bar.objects.get(pk=bar.pk)
        self.assertEqual(db_bar.serves_cocktails, place.bar.serves_cocktails)

    def test_get_or_create_initial_get_does_not_leave_stale_reverse_o2o_cache(self):
        """
        Regression test for #36489 (initial get() path, created=False).

        get_or_create() must behave consistently on every path where it
        returns an existing object. The IntegrityError fallback is one such
        path; the initial get() is the other. Whether a caller hits one or
        the other is decided by a non-deterministic race, so the observable
        state of the returned relation must not differ between them. After
        get_or_create() returns created=False, the reverse OneToOne relation
        must reflect the returned object, not a stale unsaved instance left
        in the cache.
        """
        place = Place.objects.create(name="Stale Cache Diner", address="Somewhere")

        # Instantiating Bar(place=place) triggers
        # ForwardManyToOneDescriptor.__set__, which (the relation being
        # one-to-one) seeds the reverse cache: place.bar -> <unsaved Bar,
        # pk=None>. The live `place` reference keeps it alive.
        Bar(place=place)

        # Precondition: the reverse cache is stale (unsaved instance).
        stale = Bar.place.field.remote_field.get_cached_value(place)
        self.assertIsNone(stale.pk)

        # Create the real row through a separate Place instance so the cache
        # on the original `place` object is not updated (emulates a
        # concurrent writer).
        real_bar = Bar.objects.create(place=Place.objects.get(pk=place.pk))

        # Exactly one query (the successful get) proves the initial-get path
        # is taken and the create / IntegrityError fallback is never reached.
        with self.assertNumQueries(1):
            bar, created = Bar.objects.get_or_create(place=place)

        self.assertFalse(created)
        self.assertEqual(bar.pk, real_bar.pk)

        # The reverse relation must now resolve to the real row, not the stale
        # unsaved instance. Without the fix, place.bar.pk is None.
        self.assertIsNotNone(place.bar.pk)
        self.assertEqual(place.bar.pk, bar.pk)

    def test_get_or_create_reverse_o2o_lookup_preserves_forward_cache(self):
        """
        _clear_stale_reverse_one_to_one_caches() must only act on concrete
        forward OneToOneFields named in the lookup.

        When a reverse accessor is used as a lookup
        (Place.objects.get_or_create(bar=...)), _meta.get_field() resolves it
        to a OneToOneRel, whose one_to_one flag is also True and whose
        remote_field points back at the forward field. The rel is not
        concrete, so the helper must skip it and leave the forward cache on
        the Bar instance untouched. That cache holds legitimate in-flight
        state (the caller is midway through bar.place = Place(...)), unlike a
        stale reverse cache, and must survive a lookup-only get_or_create().
        """
        old_place = Place.objects.create(name="Old Diner", address="Somewhere")
        bar = Bar.objects.create(place=old_place)

        # Begin reassigning bar to a brand-new Place. The forward descriptor
        # sets bar.place_id = None and caches the unsaved instance.
        pending = Place(name="New Diner", address="Elsewhere")
        bar.place = pending
        self.assertIsNone(bar.place_id)
        self.assertFalse(pending._is_pk_set())

        # bar itself is saved, so the lookup joins on bar.pk; the database row
        # still points at old_place, so the initial get() succeeds and the
        # helper runs.
        with self.assertNumQueries(1):
            found, created = Place.objects.get_or_create(bar=bar)

        self.assertFalse(created)
        self.assertEqual(found, old_place)

        # The in-flight forward assignment must survive the lookup.
        self.assertIs(bar.place, pending)
        self.assertIsNone(bar.place_id)

    def test_get_or_create_clears_stale_reverse_o2o_cache_for_proxy_target(self):
        """
        The OneToOneField may target a proxy model while the caller passes a
        concrete instance as the lookup value. Comparing the value against the
        concrete model lets the helper still recognize it and clear a stale
        reverse one-to-one cache.
        """
        place = Place.objects.create(name="Proxy Diner", address="Somewhere")
        field = PlaceProxyPointer._meta.get_field("place")

        # Seed the reverse cache on the concrete place with an unsaved pointer.
        stale = PlaceProxyPointer(place=ProxyPlace.objects.get(pk=place.pk))
        field.remote_field.set_cached_value(place, stale)
        self.assertTrue(stale._state.adding)

        # Create the real row through a separate instance (emulating a
        # concurrent writer) so the cache on place is not refreshed.
        real = PlaceProxyPointer.objects.create(
            place=ProxyPlace.objects.get(pk=place.pk)
        )

        # Pass the concrete Place instance as the lookup value.
        pointer, created = PlaceProxyPointer.objects.get_or_create(place=place)
        self.assertFalse(created)
        self.assertEqual(pointer.pk, real.pk)

        # The stale unsaved pointer must have been cleared from the cache.
        self.assertFalse(field.remote_field.is_cached(place))

    def test_get_or_create_clears_stale_composite_pk_reverse_o2o_cache(self):
        """
        Regression test for #36489 (composite primary key variant).

        _clear_stale_reverse_one_to_one_caches() detects unsaved instances via
        _state.adding, so it works regardless of the primary key shape. With a
        CompositePrimaryKey an unsaved instance has pk = (None, <value>) — a
        tuple, not None — which a scalar `pk is None` check would mishandle.
        """
        place = Place.objects.create(name="Composite Race Diner", address="Somewhere")
        Branch.objects.create(place=place, number=1)

        # Seed the reverse cache with an unsaved Branch instance. place_id is
        # None (not yet assigned), so pk == (None, 2) — a tuple, not None.
        stale = Branch(number=2)
        place_field = Branch._meta.get_field("place")
        place_field.remote_field.set_cached_value(place, stale)

        # Precondition: pk is a tuple (not None) but the instance is unsaved.
        self.assertIsNotNone(stale.pk)
        self.assertTrue(stale._state.adding)

        branch, created = Branch.objects.get_or_create(place=place, number=1)
        self.assertFalse(created)

        # The reverse cache must hold the saved branch, not the stale instance.
        self.assertTrue(place.branch._is_pk_set())
        self.assertEqual(place.branch.pk, branch.pk)
