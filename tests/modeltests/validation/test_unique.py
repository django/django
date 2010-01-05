import unittest
from django.conf import settings
from django.db import connection
from models import CustomPKModel, UniqueTogetherModel, UniqueFieldsModel, UniqueForDateModel, ModelToValidate


class GetUniqueCheckTests(unittest.TestCase):
    def test_unique_fields_get_collected(self):
        m = UniqueFieldsModel()
        self.assertEqual(
            ([('id',), ('unique_charfield',), ('unique_integerfield',)], []),
            m._get_unique_checks()
        )

    def test_unique_together_gets_picked_up(self):
        m = UniqueTogetherModel()
        self.assertEqual(
            ([('ifield', 'cfield',),('ifield', 'efield'), ('id',), ], []),
            m._get_unique_checks()
        )

    def test_primary_key_is_considered_unique(self):
        m = CustomPKModel()
        self.assertEqual(([('my_pk_field',)], []), m._get_unique_checks())

    def test_unique_for_date_gets_picked_up(self):
        m = UniqueForDateModel()
        self.assertEqual((
                [('id',)],
                [('date', 'count', 'start_date'), ('year', 'count', 'end_date'), ('month', 'order', 'end_date')]
            ), m._get_unique_checks()
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

    def test_primary_key_unique_check_performed_when_adding(self):
        """Regression test for #12132"""
        l = len(connection.queries)
        mtv = ModelToValidate(number=10, name='Some Name')
        setattr(mtv, '_adding', True)
        mtv.full_validate()
        self.assertEqual(l+1, len(connection.queries))

    def test_primary_key_unique_check_not_performed_when_not_adding(self):
        """Regression test for #12132"""
        l = len(connection.queries)
        mtv = ModelToValidate(number=10, name='Some Name')
        mtv.full_validate()
        self.assertEqual(l, len(connection.queries))
