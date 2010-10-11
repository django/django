from django.conf import settings
from django.utils import unittest

class SettingsTests(unittest.TestCase):

    #
    # Regression tests for #10130: deleting settings.
    #

    def test_settings_delete(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        del settings.TEST
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    def test_settings_delete_wrapped(self):
        self.assertRaises(TypeError, delattr, settings, '_wrapped')
