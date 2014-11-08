import datetime
import json
import unittest

from django.core import serializers
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from psycopg2.extras import NumericRange, DateTimeTZRange, DateRange

from .models import RangesModel


def skipUnlessPG92(test):
    if not connection.vendor == 'postgresql':
        return unittest.skip('PostgreSQL required')(test)
    PG_VERSION = connection.pg_version
    if PG_VERSION < 90200:
        return unittest.skip('PostgreSQL >= 9.2 required')(test)
    return test


@skipUnlessPG92
class TestSaveLoad(TestCase):

    def test_all_fields(self):
        now = timezone.now()
        instance = RangesModel(
            ints=NumericRange(0, 10),
            bigints=NumericRange(10, 20),
            floats=NumericRange(20, 30),
            timestamps=DateTimeTZRange(now - datetime.timedelta(hours=1), now),
            dates=DateRange(now.date() - datetime.timedelta(days=1), now.date()),
        )
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(instance.ints, loaded.ints)
        self.assertEqual(instance.bigints, loaded.bigints)
        self.assertEqual(instance.floats, loaded.floats)
        self.assertEqual(instance.timestamps, loaded.timestamps)
        self.assertEqual(instance.dates, loaded.dates)

    def test_range_object(self):
        r = NumericRange(0, 10)
        instance = RangesModel(ints=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.ints)

    def test_tuple(self):
        instance = RangesModel(ints=(0, 10))
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(NumericRange(0, 10), loaded.ints)

    def test_range_object_boundaries(self):
        r = NumericRange(0, 10, '[]')
        instance = RangesModel(floats=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.floats)
        self.assertTrue(10 in loaded.floats)

    def test_unbounded(self):
        r = NumericRange(None, None, '()')
        instance = RangesModel(floats=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.floats)

    def test_empty(self):
        r = NumericRange(empty=True)
        instance = RangesModel(ints=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.ints)

    def test_null(self):
        instance = RangesModel(ints=None)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(None, loaded.ints)


@skipUnlessPG92
class TestQuerying(TestCase):

    def setUp(self):
        self.objs = [
            RangesModel.objects.create(ints=NumericRange(0, 10)),
            RangesModel.objects.create(ints=NumericRange(5, 15)),
            RangesModel.objects.create(ints=NumericRange(None, 0)),
            RangesModel.objects.create(ints=NumericRange(empty=True)),
            RangesModel.objects.create(ints=None),
        ]

    def test_exact(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__exact=NumericRange(0, 10)),
            [self.objs[0]],
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__isnull=True),
            [self.objs[4]],
        )

    def test_isempty(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__isempty=True),
            [self.objs[3]],
        )

    def test_contains(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__contains=8),
            [self.objs[0], self.objs[1]],
        )

    def test_contains_range(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__contains=NumericRange(3, 8)),
            [self.objs[0]],
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__contained_by=NumericRange(0, 20)),
            [self.objs[0], self.objs[1], self.objs[3]],
        )

    def test_overlap(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__overlap=NumericRange(3, 8)),
            [self.objs[0], self.objs[1]],
        )

    def test_fully_lt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__fully_lt=NumericRange(5, 10)),
            [self.objs[2]],
        )

    def test_fully_gt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__fully_gt=NumericRange(5, 10)),
            [],
        )

    def test_not_lt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__not_lt=NumericRange(5, 10)),
            [self.objs[1]],
        )

    def test_not_gt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__not_gt=NumericRange(5, 10)),
            [self.objs[0], self.objs[2]],
        )

    def test_adjacent_to(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__adjacent_to=NumericRange(0, 5)),
            [self.objs[1], self.objs[2]],
        )

    def test_startswith(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__startswith=0),
            [self.objs[0]],
        )

    def test_endswith(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__endswith=0),
            [self.objs[2]],
        )


@skipUnlessPG92
class TestSerialization(TestCase):
    test_data = '[{"fields": {"ints": "{\\"upper\\": 10, \\"lower\\": 0, \\"bounds\\": \\"[)\\"}", "floats": "{\\"empty\\": true}", "bigints": null, "timestamps": null, "dates": null}, "model": "postgres_tests.rangesmodel", "pk": null}]'

    def test_dumping(self):
        instance = RangesModel(ints=NumericRange(0, 10), floats=NumericRange(empty=True))
        data = serializers.serialize('json', [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = list(serializers.deserialize('json', self.test_data))[0].object
        self.assertEqual(instance.ints, NumericRange(0, 10))
        self.assertEqual(instance.floats, NumericRange(empty=True))
        self.assertEqual(instance.dates, None)
