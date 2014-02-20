from django.test import TestCase

from django.contrib.formtools.wizard.storage import get_storage, MissingStorage
from django.contrib.formtools.wizard.storage.base import BaseStorage


class TestLoadStorage(TestCase):
    def test_load_storage(self):
        self.assertEqual(
            type(get_storage('django.contrib.formtools.wizard.storage.base.BaseStorage', 'wizard1')),
            BaseStorage)

    def test_missing_storage(self):
        self.assertRaises(MissingStorage, get_storage,
            'django.contrib.formtools.wizard.storage.idontexist.IDontExistStorage', 'wizard1')
        self.assertRaises(MissingStorage, get_storage,
            'django.contrib.formtools.wizard.storage.base.IDontExistStorage', 'wizard1')
