'''
Tests for django/utils/typecasting.py
'''
from unittest.mock import patch, call

from django.utils.typecasting import cast_boolean, force_cast_boolean
from django.test import SimpleTestCase


class BooleanCastingTests(SimpleTestCase):

    def test_int_casting(self):
        self.assertIsInstance(cast_boolean(1), bool)
        self.assertEqual(cast_boolean(1), True)
        self.assertIsInstance(cast_boolean(0), bool)
        self.assertEqual(cast_boolean(0), False)

    def test_valid_string_casting(self):
        self.assertIsInstance(cast_boolean('False'), bool)
        self.assertEqual(cast_boolean('False'), False)
        with patch('django.utils.typecasting.strtobool') as mock_strtobool:
            cast_boolean('False')
            mock_strtobool.assert_has_calls([call('False')])

    def test_invalid_string_casting(self):
        self.assertEqual(cast_boolean('kittens'), 'kittens')

    def test_invalid_object_casting(self):
        self.assertEqual(cast_boolean([]), [])

    def test_forced_valid_string_casting(self):
        self.assertIsInstance(force_cast_boolean('True'), bool)
        self.assertEqual(force_cast_boolean('True'), True)

    def test_forced_invalid_string_casting(self):
        with self.assertRaises(TypeError):
            force_cast_boolean('kittens')

    def test_forced_invalid_object_casting(self):
        with self.assertRaises(TypeError):
            force_cast_boolean([])
