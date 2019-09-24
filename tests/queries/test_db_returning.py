import datetime

from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from .models import DumbCategory, NonIntegerPKReturningModel, ReturningModel


@skipUnlessDBFeature('can_return_columns_from_insert')
class ReturningValuesTests(TestCase):
    def test_insert_returning(self):
        with CaptureQueriesContext(connection) as captured_queries:
            DumbCategory.objects.create()
        self.assertIn(
            'RETURNING %s.%s' % (
                connection.ops.quote_name(DumbCategory._meta.db_table),
                connection.ops.quote_name(DumbCategory._meta.get_field('id').column),
            ),
            captured_queries[-1]['sql'],
        )

    def test_insert_returning_non_integer(self):
        obj = NonIntegerPKReturningModel.objects.create()
        self.assertTrue(obj.created)
        self.assertIsInstance(obj.created, datetime.datetime)

    def test_insert_returning_multiple(self):
        with CaptureQueriesContext(connection) as captured_queries:
            obj = ReturningModel.objects.create()
        table_name = connection.ops.quote_name(ReturningModel._meta.db_table)
        self.assertIn(
            'RETURNING %s.%s, %s.%s' % (
                table_name,
                connection.ops.quote_name(ReturningModel._meta.get_field('id').column),
                table_name,
                connection.ops.quote_name(ReturningModel._meta.get_field('created').column),
            ),
            captured_queries[-1]['sql'],
        )
        self.assertTrue(obj.pk)
        self.assertIsInstance(obj.created, datetime.datetime)

    @skipUnlessDBFeature('can_return_rows_from_bulk_insert')
    def test_bulk_insert(self):
        objs = [ReturningModel(), ReturningModel(pk=2 ** 11), ReturningModel()]
        ReturningModel.objects.bulk_create(objs)
        for obj in objs:
            with self.subTest(obj=obj):
                self.assertTrue(obj.pk)
                self.assertIsInstance(obj.created, datetime.datetime)
