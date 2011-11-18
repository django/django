from django.core.exceptions import ValidationError
from django.db import models
from django.utils.unittest import TestCase


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
            self.assertEqual(str(e), "AutoFields must have primary_key=True.")

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
                u"'foo' value has an invalid format. It must be "
                u"in YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format."])

        # Correct format but invalid date
        self.assertRaises(ValidationError, f.clean, '2011-10-32', None)
        try:
            f.clean('2011-10-32', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'2011-10-32' value has the correct format "
                u"(YYYY-MM-DD) but it is an invalid date."])

        # Correct format but invalid date/time
        self.assertRaises(ValidationError, f.clean, '2011-10-32 10:10', None)
        try:
            f.clean('2011-10-32 10:10', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'2011-10-32 10:10' value has the correct format "
                u"(YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]) "
                u"but it is an invalid date/time."])

    def test_time_field_raises_error_message(self):
        f = models.TimeField()
        # Wrong format
        self.assertRaises(ValidationError, f.clean, 'foo', None)
        try:
            f.clean('foo', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'foo' value has an invalid format. It must be in "
                u"HH:MM[:ss[.uuuuuu]] format."])
        # Correct format but invalid time
        self.assertRaises(ValidationError, f.clean, '25:50', None)
        try:
            f.clean('25:50', None)
        except ValidationError, e:
            self.assertEqual(e.messages, [
                u"'25:50' value has the correct format "
                u"(HH:MM[:ss[.uuuuuu]]) but it is an invalid time."])
