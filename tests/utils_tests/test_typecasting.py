'''
Tests for django/utils/typecasting.py
'''
from unittest.mock import call, patch

from django.test import SimpleTestCase
from django.utils.typecasting import cast_boolean_from_field, force_cast_boolean


class BooleanCastingTests(SimpleTestCase):

    def test_falsey_string_casting(self):
        self.assertIsInstance(cast_boolean_from_field('False'), bool)
        self.assertIs(cast_boolean_from_field('False'), False)

    def test_truthy_string_casting(self):
        self.assertIsInstance(cast_boolean_from_field('True'), bool)
        self.assertIs(cast_boolean_from_field('True'), True)

    def test_string_casting(self):
        self.assertIs(cast_boolean_from_field('kittens'), True)

    def test_string_casting_uses_strtobool(self):
        with patch('django.utils.typecasting.strtobool') as mock_strtobool:
            cast_boolean_from_field('False')
            mock_strtobool.assert_has_calls([call('False')])

    def test_empty_string_casting(self):
        self.assertIs(cast_boolean_from_field(''), None)

    def test_none_casting(self):
        self.assertIs(cast_boolean_from_field(None), None)

    def test_int_casting(self):
        self.assertIsInstance(cast_boolean_from_field(1), bool)
        self.assertIs(cast_boolean_from_field(1), True)
        self.assertIsInstance(cast_boolean_from_field(0), bool)
        self.assertIs(cast_boolean_from_field(0), False)

    def test_invalid_object_casting(self):
        self.assertEqual(cast_boolean_from_field([]), [])


class BooleanForcedCastingTests(SimpleTestCase):

    def test_forced_falsey_string_casting(self):
        self.assertIsInstance(force_cast_boolean('False'), bool)
        self.assertIs(force_cast_boolean('False'), False)

    def test_forced_truthy_string_casting(self):
        self.assertIsInstance(force_cast_boolean('True'), bool)
        self.assertIs(force_cast_boolean('True'), True)

    def test_forced_string_casting(self):
        with self.assertRaises(BaseException):
            force_cast_boolean('kittens')

    def test_forced_string_casting_uses_strtobool(self):
        with patch('django.utils.typecasting.strtobool') as mock_strtobool:
            force_cast_boolean('False')
            mock_strtobool.assert_has_calls([call('False')])

    def test_forced_empty_string_casting(self):
        with self.assertRaises(BaseException):
            force_cast_boolean('')

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
