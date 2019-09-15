import datetime
import uuid

from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from .models import DumbCategory, NonIntegerPKReturningModel, ReturningModel


class UUIDExtensionTestCase(TestCase):
    def setUp(self):
        super().setUp()
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')


@skipUnlessDBFeature("can_return_columns_from_insert")
class ReturningValuesTests(UUIDExtensionTestCase):
    def test_insert_returning(self):
        with CaptureQueriesContext(connection) as captured_queries:
            DumbCategory.objects.create()
        self.assertIn(
            "RETURNING %s.%s"
            % (
                connection.ops.quote_name(DumbCategory._meta.db_table),
                connection.ops.quote_name(DumbCategory._meta.get_field("id").column),
            ),
            captured_queries[-1]["sql"],
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
            "RETURNING %s.%s, %s.%s"
            % (
                table_name,
                connection.ops.quote_name(ReturningModel._meta.get_field("id").column),
                table_name,
                connection.ops.quote_name(
                    ReturningModel._meta.get_field("created").column
                ),
            ),
            captured_queries[-1]["sql"],
        )
        self.assertTrue(obj.pk)
        self.assertIsInstance(obj.created, datetime.datetime)

    @skipUnlessDBFeature("can_return_rows_from_bulk_insert")
    def test_bulk_insert(self):
        objs = [ReturningModel(), ReturningModel(pk=2**11), ReturningModel()]
        ReturningModel.objects.bulk_create(objs)
        for obj in objs:
            with self.subTest(obj=obj):
                self.assertTrue(obj.pk)
                self.assertIsInstance(obj.created, datetime.datetime)


@skipUnlessDBFeature("can_return_columns_from_insert")
class DatabaseDefaultsTests(UUIDExtensionTestCase):
    def test_now(self):
        obj = ReturningModel.objects.create()
        self.assertIsInstance(obj.created, datetime.datetime)

    def test_truncate(self):
        obj = ReturningModel.objects.create()
        self.assertIsInstance(obj.year, int)

    def test_pi(self):
        obj = ReturningModel.objects.create()
        self.assertAlmostEqual(obj.pi, 3.1415926535897)  # decimal precision varies

    def test_expression_wrapper(self):
        obj = ReturningModel.objects.create()
        self.assertEqual(obj.expr_wrapper, 3)

    def test_coalesce_value(self):
        obj = ReturningModel.objects.create()
        self.assertEqual(obj.coalesce_val, 1337)

    def test_raw_sql(self):
        obj = ReturningModel.objects.create()
        self.assertEqual(obj.raw_sql, 75)

    def test_custom_uuid(self):
        obj = ReturningModel.objects.create()
        self.assertIsInstance(obj.uuid, uuid.UUID)

    def test_boolean_function(self):
        obj = ReturningModel.objects.create()
        self.assertIsInstance(obj.is_odd, bool)
        self.assertFalse(obj.is_odd)
