import unittest

from models import CustomPKModel, UniqueTogetherModel, UniqueFieldsModel, UniqueForDateModel

class GetUniqueCheckTests(unittest.TestCase):
    def test_unique_fields_get_collected(self):
        m = UniqueFieldsModel()
        self.assertEqual(([('id',), ('unique_charfield',), ('unique_integerfield',)], []), m._get_unique_checks())

    def test_unique_together_gets_picked_up(self):
        m = UniqueTogetherModel()
        self.assertEqual(([('ifield', 'cfield',),('ifield', 'efield'), ('id',), ], []), m._get_unique_checks())

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



