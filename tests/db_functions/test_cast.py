from django.db import models
from django.db.models.expressions import Value
from django.db.models.functions import Cast
from django.test import TestCase

from .models import Author


class CastTests(TestCase):
    @classmethod
    def setUpTestData(self):
        Author.objects.create(name='Bob', age=1)

    def test_cast_from_value(self):
        numbers = Author.objects.annotate(cast_integer=Cast(Value('0'), models.IntegerField()))
        self.assertEqual(numbers.get().cast_integer, 0)

    def test_cast_from_field(self):
        numbers = Author.objects.annotate(cast_string=Cast('age', models.CharField(max_length=255)),)
        self.assertEqual(numbers.get().cast_string, '1')

    def test_cast_from_python(self):
        numbers = Author.objects.annotate(cast_float=Cast(0, models.FloatField()))
        self.assertEqual(numbers.get().cast_float, 0.0)
