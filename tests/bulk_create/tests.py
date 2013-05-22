from __future__ import absolute_import

from operator import attrgetter

from django.db import connection
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import override_settings

from .models import Country, Restaurant, Pizzeria, State, TwoFields


class BulkCreateTests(TestCase):
    def setUp(self):
        self.data = [
            Country(name="United States of America", iso_two_letter="US"),
            Country(name="The Netherlands", iso_two_letter="NL"),
            Country(name="Germany", iso_two_letter="DE"),
            Country(name="Czech Republic", iso_two_letter="CZ")
        ]

    def test_simple(self):
        created = Country.objects.bulk_create(self.data)
        self.assertEqual(len(created), 4)
        self.assertQuerysetEqual(Country.objects.order_by("-name"), [
            "United States of America", "The Netherlands", "Germany", "Czech Republic"
        ], attrgetter("name"))

        created = Country.objects.bulk_create([])
        self.assertEqual(created, [])
        self.assertEqual(Country.objects.count(), 4)

    @skipUnlessDBFeature('has_bulk_insert')
    def test_efficiency(self):
        with self.assertNumQueries(1):
            Country.objects.bulk_create(self.data)

    def test_inheritance(self):
        Restaurant.objects.bulk_create([
            Restaurant(name="Nicholas's")
        ])
        self.assertQuerysetEqual(Restaurant.objects.all(), [
            "Nicholas's",
        ], attrgetter("name"))
        with self.assertRaises(ValueError):
            Pizzeria.objects.bulk_create([
                Pizzeria(name="The Art of Pizza")
            ])
        self.assertQuerysetEqual(Pizzeria.objects.all(), [])
        self.assertQuerysetEqual(Restaurant.objects.all(), [
            "Nicholas's",
        ], attrgetter("name"))

    def test_non_auto_increment_pk(self):
        State.objects.bulk_create([
            State(two_letter_code=s)
            for s in ["IL", "NY", "CA", "ME"]
        ])
        self.assertQuerysetEqual(State.objects.order_by("two_letter_code"), [
            "CA", "IL", "ME", "NY",
        ], attrgetter("two_letter_code"))

    @skipUnlessDBFeature('has_bulk_insert')
    def test_non_auto_increment_pk_efficiency(self):
        with self.assertNumQueries(1):
            State.objects.bulk_create([
                State(two_letter_code=s)
                for s in ["IL", "NY", "CA", "ME"]
            ])
        self.assertQuerysetEqual(State.objects.order_by("two_letter_code"), [
            "CA", "IL", "ME", "NY",
        ], attrgetter("two_letter_code"))

    @skipIfDBFeature('allows_primary_key_0')
    def test_zero_as_autoval(self):
        """
        Zero as id for AutoField should raise exception in MySQL, because MySQL
        does not allow zero for automatic primary key.
        """

        valid_country = Country(name='Germany', iso_two_letter='DE')
        invalid_country = Country(id=0, name='Poland', iso_two_letter='PL')
        with self.assertRaises(ValueError):
            Country.objects.bulk_create([valid_country, invalid_country])

    def test_batch_same_vals(self):
        # Sqlite had a problem where all the same-valued models were
        # collapsed to one insert.
        Restaurant.objects.bulk_create([
            Restaurant(name='foo') for i in range(0, 2)
        ])
        self.assertEqual(Restaurant.objects.count(), 2)

    def test_large_batch(self):
        with override_settings(DEBUG=True):
            connection.queries = []
            TwoFields.objects.bulk_create([
                   TwoFields(f1=i, f2=i+1) for i in range(0, 1001)
                ])
        self.assertEqual(TwoFields.objects.count(), 1001)
        self.assertEqual(
            TwoFields.objects.filter(f1__gte=450, f1__lte=550).count(),
            101)
        self.assertEqual(TwoFields.objects.filter(f2__gte=901).count(), 101)

    @skipUnlessDBFeature('has_bulk_insert')
    def test_large_single_field_batch(self):
        # SQLite had a problem with more than 500 UNIONed selects in single
        # query.
        Restaurant.objects.bulk_create([
            Restaurant() for i in range(0, 501)
        ])

    @skipUnlessDBFeature('has_bulk_insert')
    def test_large_batch_efficiency(self):
        with override_settings(DEBUG=True):
            connection.queries = []
            TwoFields.objects.bulk_create([
                   TwoFields(f1=i, f2=i+1) for i in range(0, 1001)
                ])
            self.assertTrue(len(connection.queries) < 10)

    def test_large_batch_mixed(self):
        """
        Test inserting a large batch with objects having primary key set
        mixed together with objects without PK set.
        """
        with override_settings(DEBUG=True):
            connection.queries = []
            TwoFields.objects.bulk_create([
                TwoFields(id=i if i % 2 == 0 else None, f1=i, f2=i+1)
                for i in range(100000, 101000)])
        self.assertEqual(TwoFields.objects.count(), 1000)
        # We can't assume much about the ID's created, except that the above
        # created IDs must exist.
        id_range = range(100000, 101000, 2)
        self.assertEqual(TwoFields.objects.filter(id__in=id_range).count(), 500)
        self.assertEqual(TwoFields.objects.exclude(id__in=id_range).count(), 500)

    @skipUnlessDBFeature('has_bulk_insert')
    def test_large_batch_mixed_efficiency(self):
        """
        Test inserting a large batch with objects having primary key set
        mixed together with objects without PK set.
        """
        with override_settings(DEBUG=True):
            connection.queries = []
            TwoFields.objects.bulk_create([
                TwoFields(id=i if i % 2 == 0 else None, f1=i, f2=i+1)
                for i in range(100000, 101000)])
            self.assertTrue(len(connection.queries) < 10)

    def test_explicit_batch_size(self):
        objs = [TwoFields(f1=i, f2=i) for i in range(0, 4)]
        TwoFields.objects.bulk_create(objs, 2)
        self.assertEqual(TwoFields.objects.count(), len(objs))
        TwoFields.objects.all().delete()
        TwoFields.objects.bulk_create(objs, len(objs))
        self.assertEqual(TwoFields.objects.count(), len(objs))

    @skipUnlessDBFeature('has_bulk_insert')
    def test_explicit_batch_size_efficiency(self):
        objs = [TwoFields(f1=i, f2=i) for i in range(0, 100)]
        with self.assertNumQueries(2):
            TwoFields.objects.bulk_create(objs, 50)
        TwoFields.objects.all().delete()
        with self.assertNumQueries(1):
            TwoFields.objects.bulk_create(objs, len(objs))
