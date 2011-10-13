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
        # primary_key must be True. Refs #12467.
        self.assertRaises(AssertionError, models.AutoField, 'primary_key', False)
        try:
            models.AutoField(primary_key=False)
        except AssertionError, e:
            self.assertEqual(e.message, u"AutoFields must have primary_key=True.")

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

    def test_date_field_raises_error_message(self):
        f = models.DateField()
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'foo' value has an invalid date format. "
                u"It must be in YYYY-MM-DD format."])

        self.assertRaises(ValidationError, f.clean, 'aaaa-10-10', None)
        try:
            f.clean('aaaa-10-10', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'aaaa-10-10' value has an invalid date format. "
                u"It must be in YYYY-MM-DD format."])

        self.assertRaises(ValidationError, f.clean, '2011-13-10', None)
        try:
            f.clean('2011-13-10', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'2011-13-10' value has the correct format (YYYY-MM-DD) "
                u"but it is an invalid date."])

        self.assertRaises(ValidationError, f.clean, '2011-10-32', None)
        try:
            f.clean('2011-10-32', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'2011-10-32' value has the correct format (YYYY-MM-DD) "
                u"but it is an invalid date."])

    def test_datetime_field_raises_error_message(self):
        f = models.DateTimeField()
        # Wrong format
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'foo' value either has an invalid valid format "
                u"(The format must be YYYY-MM-DD HH:MM[:ss[.uuuuuu]]) "
                u"or is an invalid date/time."])
        self.assertRaises(ValidationError, f.clean,
                          '2011-10-32 10:10', None)
        # Correct format but invalid date/time
        try:
            f.clean('2011-10-32 10:10', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'2011-10-32 10:10' value either has an invalid valid format "
                u"(The format must be YYYY-MM-DD HH:MM[:ss[.uuuuuu]]) "
                u"or is an invalid date/time."])