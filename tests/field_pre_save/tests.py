import unittest
from datetime import datetime

from django.test import TestCase

from .models import Article


class PreSaveTests(TestCase):
    def test_field_pre_save_default(self):
        a = Article()
        self.assertIsNone(a.update_date)
        a.save()
        self.assertIsInstance(a.update_date, datetime)

    @unittest.mock.patch('django.db.models.DateTimeField.pre_save')
    def test_field_pre_save_force_insert(self, pre_save):
        pre_save.return_value = datetime.now()
        a = Article(pk=1)
        a.save(force_insert=True)
        a.save()
        self.assertListEqual(pre_save.call_args_list, [
            unittest.mock.call(unittest.mock.ANY, True),
            unittest.mock.call(unittest.mock.ANY, False)
        ])
