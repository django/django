from operator import attrgetter

from django.db import connection
from django.db.models import FileField, Value
from django.db.models.functions import Lower
from django.test import (
    TestCase, override_settings, skipIfDBFeature, skipUnlessDBFeature,
)

from .models import (
    Country, NoFields, NullableFields, Pizzeria, ProxyCountry,
    ProxyMultiCountry, ProxyMultiProxyCountry, ProxyProxyCountry, Restaurant,
    State, TwoFields,
)


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

    def test_multi_table_inheritance_unsupported(self):
        expected_message = "Can't bulk create a multi-table inherited model"
        with self.assertRaisesMessage(ValueError, expected_message):
            Pizzeria.objects.bulk_create([
                Pizzeria(name="The Art of Pizza"),
            ])
        with self.assertRaisesMessage(ValueError, expected_message):
            ProxyMultiCountry.objects.bulk_create([
                ProxyMultiCountry(name="Fillory", iso_two_letter="FL"),
            ])
        with self.assertRaisesMessage(ValueError, expected_message):
            ProxyMultiProxyCountry.objects.bulk_create([
                ProxyMultiProxyCountry(name="Fillory", iso_two_letter="FL"),
            ])

    def test_proxy_inheritance_supported(self):
        ProxyCountry.objects.bulk_create([
            ProxyCountry(name="Qwghlm", iso_two_letter="QW"),
            Country(name="Tortall", iso_two_letter="TA"),
        ])
        self.assertQuerysetEqual(ProxyCountry.objects.all(), {
            "Qwghlm", "Tortall"
        }, attrgetter("name"), ordered=False)

        ProxyProxyCountry.objects.bulk_create([
            ProxyProxyCountry(name="Netherlands", iso_two_letter="NT"),
        ])
        self.assertQuerysetEqual(ProxyProxyCountry.objects.all(), {
            "Qwghlm", "Tortall", "Netherlands",
        }, attrgetter("name"), ordered=False)

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

    @skipIfDBFeature('allows_auto_pk_0')
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
            connection.queries_log.clear()
            TwoFields.objects.bulk_create([
                TwoFields(f1=i, f2=i + 1) for i in range(0, 1001)
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
            connection.queries_log.clear()
            TwoFields.objects.bulk_create([
                TwoFields(f1=i, f2=i + 1) for i in range(0, 1001)
            ])
            self.assertLess(len(connection.queries), 10)

    def test_large_batch_mixed(self):
        """
        Test inserting a large batch with objects having primary key set
        mixed together with objects without PK set.
        """
        with override_settings(DEBUG=True):
            connection.queries_log.clear()
            TwoFields.objects.bulk_create([
                TwoFields(id=i if i % 2 == 0 else None, f1=i, f2=i + 1)
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
            connection.queries_log.clear()
            TwoFields.objects.bulk_create([
                TwoFields(id=i if i % 2 == 0 else None, f1=i, f2=i + 1)
                for i in range(100000, 101000)])
            self.assertLess(len(connection.queries), 10)

    def test_explicit_batch_size(self):
        objs = [TwoFields(f1=i, f2=i) for i in range(0, 4)]
        num_objs = len(objs)
        TwoFields.objects.bulk_create(objs, batch_size=1)
        self.assertEqual(TwoFields.objects.count(), num_objs)
        TwoFields.objects.all().delete()
        TwoFields.objects.bulk_create(objs, batch_size=2)
        self.assertEqual(TwoFields.objects.count(), num_objs)
        TwoFields.objects.all().delete()
        TwoFields.objects.bulk_create(objs, batch_size=3)
        self.assertEqual(TwoFields.objects.count(), num_objs)
        TwoFields.objects.all().delete()
        TwoFields.objects.bulk_create(objs, batch_size=num_objs)
        self.assertEqual(TwoFields.objects.count(), num_objs)

    def test_empty_model(self):
        NoFields.objects.bulk_create([NoFields() for i in range(2)])
        self.assertEqual(NoFields.objects.count(), 2)

    @skipUnlessDBFeature('has_bulk_insert')
    def test_explicit_batch_size_efficiency(self):
        objs = [TwoFields(f1=i, f2=i) for i in range(0, 100)]
        with self.assertNumQueries(2):
            TwoFields.objects.bulk_create(objs, 50)
        TwoFields.objects.all().delete()
        with self.assertNumQueries(1):
            TwoFields.objects.bulk_create(objs, len(objs))

    @skipUnlessDBFeature('has_bulk_insert')
    def test_bulk_insert_expressions(self):
        Restaurant.objects.bulk_create([
            Restaurant(name="Sam's Shake Shack"),
            Restaurant(name=Lower(Value("Betty's Beetroot Bar")))
        ])
        bbb = Restaurant.objects.filter(name="betty's beetroot bar")
        self.assertEqual(bbb.count(), 1)

    @skipUnlessDBFeature('has_bulk_insert')
    def test_bulk_insert_nullable_fields(self):
        # NULL can be mixed with other values in nullable fields
        nullable_fields = [field for field in NullableFields._meta.get_fields() if field.name != 'id']
        NullableFields.objects.bulk_create([
            NullableFields(**{field.name: None}) for field in nullable_fields
        ])
        self.assertEqual(NullableFields.objects.count(), len(nullable_fields))
        for field in nullable_fields:
            with self.subTest(field=field):
                field_value = '' if isinstance(field, FileField) else None
                self.assertEqual(NullableFields.objects.filter(**{field.name: field_value}).count(), 1)

    @skipUnlessDBFeature('can_return_ids_from_bulk_insert')
    def test_set_pk_and_insert_single_item(self):
        with self.assertNumQueries(1):
            countries = Country.objects.bulk_create([self.data[0]])
        self.assertEqual(len(countries), 1)
        self.assertEqual(Country.objects.get(pk=countries[0].pk), countries[0])

    @skipUnlessDBFeature('can_return_ids_from_bulk_insert')
    def test_set_pk_and_query_efficiency(self):
        with self.assertNumQueries(1):
            countries = Country.objects.bulk_create(self.data)
        self.assertEqual(len(countries), 4)
        self.assertEqual(Country.objects.get(pk=countries[0].pk), countries[0])
        self.assertEqual(Country.objects.get(pk=countries[1].pk), countries[1])
        self.assertEqual(Country.objects.get(pk=countries[2].pk), countries[2])
        self.assertEqual(Country.objects.get(pk=countries[3].pk), countries[3])

    @skipUnlessDBFeature('can_return_ids_from_bulk_insert')
    def test_set_state(self):
        country_nl = Country(name='Netherlands', iso_two_letter='NL')
        country_be = Country(name='Belgium', iso_two_letter='BE')
        Country.objects.bulk_create([country_nl])
        country_be.save()
        # Objects save via bulk_create() and save() should have equal state.
        self.assertEqual(country_nl._state.adding, country_be._state.adding)
        self.assertEqual(country_nl._state.db, country_be._state.db)
