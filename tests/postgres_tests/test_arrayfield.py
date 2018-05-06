from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase


class ArrayFieldTests(TestCase):

    def test_to_python(self):
        f = ArrayField(models.CharField(max_length=10))
        self.assertEqual(f.to_python(['foo', 'bar']), ['foo', 'bar'])
        self.assertEqual(f.to_python('["foo", "bar"]'), ['foo', 'bar'])
        with self.assertRaises(ValueError):
            f.to_python('foo')


class ValidationTest(TestCase):

    def test_clean(self):
        f = ArrayField(models.CharField(max_length=10))
        self.assertEqual(['foo', 'bar'], f.clean(['foo', 'bar'], None))

        msg = ("['Item 1 in the array did not validate: "
               "Ensure this value has at most 10 characters (it has 11).']")
        with self.assertRaisesMessage(ValidationError, msg):
            self.assertEqual(['bar'], f.clean(['1234567890a'], None))

    def test_clean_nested(self):
        f = ArrayField(
            ArrayField(models.CharField(max_length=10))
        )
        self.assertEqual(
            [['foo', 'bar'], ['foo', 'bar']],
            f.clean([['foo', 'bar'], ['foo', 'bar']], None)
        )

        msg = 'Nested arrays must have the same length.'
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean([['foo', 'bar'], ['foo']], None)
