import unittest
import datetime
from django.conf import settings
from django.db import connection
from models import CustomPKModel, UniqueTogetherModel, UniqueFieldsModel, UniqueForDateModel, ModelToValidate


class GetUniqueCheckTests(unittest.TestCase):
    def test_unique_fields_get_collected(self):
        m = UniqueFieldsModel()
        self.assertEqual(
            ([(UniqueFieldsModel, ('id',)),
              (UniqueFieldsModel, ('unique_charfield',)),
              (UniqueFieldsModel, ('unique_integerfield',))],
             []),
            m._get_unique_checks()
        )

    def test_unique_together_gets_picked_up_and_converted_to_tuple(self):
        m = UniqueTogetherModel()
        self.assertEqual(
            ([(UniqueTogetherModel, ('ifield', 'cfield',)),
              (UniqueTogetherModel, ('ifield', 'efield')),
              (UniqueTogetherModel, ('id',)), ],
             []),
            m._get_unique_checks()
        )

    def test_primary_key_is_considered_unique(self):
        m = CustomPKModel()
        self.assertEqual(([(CustomPKModel, ('my_pk_field',))], []), m._get_unique_checks())

    def test_unique_for_date_gets_picked_up(self):
        m = UniqueForDateModel()
        self.assertEqual((
            [(UniqueForDateModel, ('id',))],
            [(UniqueForDateModel, 'date', 'count', 'start_date'),
             (UniqueForDateModel, 'year', 'count', 'end_date'),
             (UniqueForDateModel, 'month', 'order', 'end_date')]
            ), m._get_unique_checks()
        )

    def test_unique_for_date_exclusion(self):
        m = UniqueForDateModel()
        self.assertEqual((
            [(UniqueForDateModel, ('id',))],
            [(UniqueForDateModel, 'year', 'count', 'end_date'),
             (UniqueForDateModel, 'month', 'order', 'end_date')]
            ), m._get_unique_checks(exclude='start_date')
        )

class PerformUniqueChecksTest(unittest.TestCase):
    def setUp(self):
        # Set debug to True to gain access to connection.queries.
        self._old_debug, settings.DEBUG = settings.DEBUG, True
        super(PerformUniqueChecksTest, self).setUp()

    def tearDown(self):
        # Restore old debug value.
        settings.DEBUG = self._old_debug
        super(PerformUniqueChecksTest, self).tearDown()

    def test_primary_key_unique_check_not_performed_when_adding_and_pk_not_specified(self):
        # Regression test for #12560
        query_count = len(connection.queries)
        mtv = ModelToValidate(number=10, name='Some Name')
        setattr(mtv, '_adding', True)
        mtv.full_clean()
        self.assertEqual(query_count, len(connection.queries))

    def test_primary_key_unique_check_performed_when_adding_and_pk_specified(self):
        # Regression test for #12560
        query_count = len(connection.queries)
        mtv = ModelToValidate(number=10, name='Some Name', id=123)
        setattr(mtv, '_adding', True)
        mtv.full_clean()
        self.assertEqual(query_count + 1, len(connection.queries))

    def test_primary_key_unique_check_not_performed_when_not_adding(self):
        # Regression test for #12132
        query_count= len(connection.queries)
        mtv = ModelToValidate(number=10, name='Some Name')
        mtv.full_clean()
        self.assertEqual(query_count, len(connection.queries))

