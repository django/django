from django.test import TestCase
from django.db import transaction, IntegrityError
from models import Place, Restaurant, Waiter, ManualPrimaryKey, RelatedModel, MultiModel

class OneToOneTests(TestCase):

    def setUp(self):
        self.p1 = Place(name='Demon Dogs', address='944 W. Fullerton')
        self.p1.save()
        self.p2 = Place(name='Ace Hardware', address='1013 N. Ashland')
        self.p2.save()
        self.r = Restaurant(place=self.p1, serves_hot_dogs=True, serves_pizza=False)
        self.r.save()

    def test_getter(self):
        # A Restaurant can access its place.
        self.assertEqual(repr(self.r.place), '<Place: Demon Dogs the place>')
        # A Place can access its restaurant, if available.
        self.assertEqual(repr(self.p1.restaurant), '<Restaurant: Demon Dogs the restaurant>')
        # p2 doesn't have an associated restaurant.
        self.assertRaises(Restaurant.DoesNotExist, getattr, self.p2, 'restaurant')

    def test_setter(self):
        # Set the place using assignment notation. Because place is the primary
        # key on Restaurant, the save will create a new restaurant
        self.r.place = self.p2
        self.r.save()
        self.assertEqual(repr(self.p2.restaurant), '<Restaurant: Ace Hardware the restaurant>')
        self.assertEqual(repr(self.r.place), '<Place: Ace Hardware the place>')
        self.assertEqual(self.p2.pk, self.r.pk)
        # Set the place back again, using assignment in the reverse direction.
        self.p1.restaurant = self.r
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
        assert_get_place(restaurant__exact=self.r)
        assert_get_place(restaurant__pk=self.p1.pk)
        assert_get_place(restaurant=self.p1.pk)
        assert_get_place(restaurant=self.r)
        assert_get_place(id__exact=self.p1.pk)
        assert_get_place(pk=self.p1.pk)

    def test_foreign_key(self):
        # Add a Waiter to the Restaurant.
        w = self.r.waiter_set.create(name='Joe')
        w.save()
        self.assertEqual(repr(w), '<Waiter: Joe the waiter at Demon Dogs the restaurant>')
        # Query the waiters
        def assert_filter_waiters(**params):
            self.assertQuerysetEqual(Waiter.objects.filter(**params), [
                '<Waiter: Joe the waiter at Demon Dogs the restaurant>'
            ])
        assert_filter_waiters(restaurant__place__exact=self.p1.pk)
        assert_filter_waiters(restaurant__place__exact=self.p1)
        assert_filter_waiters(restaurant__place__pk=self.p1.pk)
        assert_filter_waiters(restaurant__exact=self.p1.pk)
        assert_filter_waiters(restaurant__exact=self.p1)
        assert_filter_waiters(restaurant__pk=self.p1.pk)
        assert_filter_waiters(restaurant=self.p1.pk)
        assert_filter_waiters(restaurant=self.r)
        assert_filter_waiters(id__exact=self.p1.pk)
        assert_filter_waiters(pk=self.p1.pk)
        # Delete the restaurant; the waiter should also be removed
        r = Restaurant.objects.get(pk=self.p1.pk)
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
        sid = transaction.savepoint()
        mm = MultiModel(link1=self.p2, link2=o1, name="x1")
        self.assertRaises(IntegrityError, mm.save)
        transaction.savepoint_rollback(sid)
