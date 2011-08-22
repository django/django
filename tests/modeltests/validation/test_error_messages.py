from django.core.exceptions import ValidationError
from django.utils.unittest import TestCase
from django.db import models


class ValidationMessagesTest(TestCase):

    def test_autofield_field_raises_error_message(self):
        f = models.AutoField(primary_key=True)
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [u"'foo' value must be an integer."])

    def test_integer_field_raises_error_message(self):
        f = models.IntegerField()
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [u"'foo' value must be an integer."])

    def test_boolean_field_raises_error_message(self):
        f = models.BooleanField()
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages,
                        [u"'foo' value must be either True or False."])

    def test_float_field_raises_error_message(self):
        f = models.FloatField()
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [u"'foo' value must be a float."])

    def test_decimal_field_raises_error_message(self):
        f = models.DecimalField()
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages,
                        [u"'foo' value must be a decimal number."])

    def test_null_boolean_field_raises_error_message(self):
        f = models.NullBooleanField()
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages,
                        [u"'foo' value must be either None, True or False."])
