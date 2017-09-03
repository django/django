'''
Tests for django/utils/typecasting.py
'''
from unittest.mock import call, patch

from django.test import SimpleTestCase
from django.utils.typecasting import cast_boolean, force_cast_boolean


class BooleanCastingTests(SimpleTestCase):

    def test_truthy_string_casting(self):
        self.assertIsInstance(cast_boolean('False'), bool)
        self.assertIs(cast_boolean('False'), False)

    def test_string_casting_uses_strtobool(self):
        with patch('django.utils.typecasting.strtobool') as mock_strtobool:
            cast_boolean('False')
            mock_strtobool.assert_has_calls([call('False')])

    def test_string_casting(self):
        self.assertIs(cast_boolean('kittens'), True)

    def test_empty_string_casting(self):
        self.assertIs(cast_boolean(''), None)

    def test_none_casting(self):
        self.assertIs(cast_boolean(None), None)

    def test_int_casting(self):
        self.assertIsInstance(cast_boolean(1), bool)
        self.assertIs(cast_boolean(1), True)
        self.assertIsInstance(cast_boolean(0), bool)
        self.assertIs(cast_boolean(0), False)

    def test_invalid_object_casting(self):
        self.assertEqual(cast_boolean([]), [])


class BooleanForcedCastingTests(SimpleTestCase):

    def test_forced_truthy_string_casting(self):
        self.assertIsInstance(force_cast_boolean('False'), bool)
        self.assertIs(force_cast_boolean('False'), False)

    def test_forced_string_casting_uses_strtobool(self):
        with patch('django.utils.typecasting.strtobool') as mock_strtobool:
            force_cast_boolean('False')
            mock_strtobool.assert_has_calls([call('False')])

    def test_forced_string_casting(self):
        with self.assertRaises(BaseException):
            force_cast_boolean('kittens')

    def test_forced_empty_string_casting(self):
        self.assertIs(force_cast_boolean(''), None)

    def test_forced_none_casting(self):
        self.assertIs(force_cast_boolean(None), None)

    def test_forced_int_casting(self):
        self.assertIsInstance(force_cast_boolean(1), bool)
        self.assertIs(force_cast_boolean(1), True)
        self.assertIsInstance(force_cast_boolean(0), bool)
        self.assertIs(force_cast_boolean(0), False)

    def test_forced_invalid_object_casting(self):
        with self.assertRaises(BaseException):
            force_cast_boolean([])
