import datetime
import decimal
import unittest

from django.conf import settings
from django.db import connection, models
from django.db.models import Avg
from django.db.models.expressions import Value
from django.db.models.functions import Cast
from django.test import (
    TestCase, ignore_warnings, override_settings, skipUnlessDBFeature,
)
from django.utils import timezone

from ..models import Author, Fan


class CastTests(TestCase):
    @classmethod
    def setUpTestData(self):
        Author.objects.create(name='Bob', age=1, alias='1')

    def test_cast_from_value(self):
        numbers = Author.objects.annotate(cast_integer=Cast(Value('0'), models.IntegerField()))
        self.assertEqual(numbers.get().cast_integer, 0)

    def test_cast_from_field(self):
        numbers = Author.objects.annotate(cast_string=Cast('age', models.CharField(max_length=255)),)
        self.assertEqual(numbers.get().cast_string, '1')

    def test_cast_to_char_field_without_max_length(self):
        numbers = Author.objects.annotate(cast_string=Cast('age', models.CharField()))
        self.assertEqual(numbers.get().cast_string, '1')

    # Silence "Truncated incorrect CHAR(1) value: 'Bob'".
    @ignore_warnings(module='django.db.backends.mysql.base')
    @skipUnlessDBFeature('supports_cast_with_precision')
    def test_cast_to_char_field_with_max_length(self):
        names = Author.objects.annotate(cast_string=Cast('name', models.CharField(max_length=1)))
        self.assertEqual(names.get().cast_string, 'B')

    def test_cast_to_integer(self):
        for field_class in (
            models.AutoField,
            models.BigAutoField,
            models.IntegerField,
            models.BigIntegerField,
            models.SmallIntegerField,
            models.PositiveIntegerField,
            models.PositiveSmallIntegerField,
        ):
            with self.subTest(field_class=field_class):
                numbers = Author.objects.annotate(cast_int=Cast('alias', field_class()))
                self.assertEqual(numbers.get().cast_int, 1)

    def test_case_from_db_datetime_to_date(self):
        author = Author.objects.create(name='John Smith', age=45)
        fan_since = datetime.datetime(2016, 2, 3, 15, 0, 0)
        if settings.USE_TZ:
            fan_since = timezone.make_aware(fan_since, is_dst=False)
        Fan.objects.create(name='Margaret', age=50, author=author, fan_since=fan_since)
        fan = Fan.objects.annotate(fan_for_day=Cast("fan_since", models.DateField())).first()
        self.assertIsInstance(fan.fan_for_day, datetime.date)

    def test_case_from_db_datetime_to_date_group_by(self):
        # Create a fan
        author = Author.objects.create(name='John Smith', age=45)
        fan_since = datetime.datetime(2016, 2, 3, 15, 0, 0)
        if settings.USE_TZ:
            fan_since = timezone.make_aware(fan_since, is_dst=False)
        Fan.objects.create(name='Margaret', age=50, author=author, fan_since=fan_since)
        fans = Fan.objects.values("author").annotate(
            fan_for_day=Cast("fan_since", models.DateField()),
            fans=models.Count("*")).values()
        self.assertIsInstance(fans[0]['fan_for_day'], datetime.date)
        self.assertEqual(fans[0]['fans'], 1)

    def test_cast_from_python_to_date(self):
        today = datetime.date.today()
        dates = Author.objects.annotate(cast_date=Cast(today, models.DateField()))
        self.assertEqual(dates.get().cast_date, today)

    def test_cast_from_python_to_datetime(self):
        now = datetime.datetime.now()
        dates = Author.objects.annotate(cast_datetime=Cast(now, models.DateTimeField()))
        self.assertEqual(dates.get().cast_datetime, now)

    def test_cast_from_python(self):
        numbers = Author.objects.annotate(cast_float=Cast(decimal.Decimal(0.125), models.FloatField()))
        cast_float = numbers.get().cast_float
        self.assertIsInstance(cast_float, float)
        self.assertEqual(cast_float, 0.125)

    @unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL test')
    @override_settings(DEBUG=True)
    def test_expression_wrapped_with_parentheses_on_postgresql(self):
        """
        The SQL for the Cast expression is wrapped with parentheses in case
        it's a complex expression.
        """
        list(Author.objects.annotate(cast_float=Cast(Avg('age'), models.FloatField())))
        self.assertIn('(AVG("db_functions_author"."age"))::double precision', connection.queries[-1]['sql'])

    def test_cast_to_text_field(self):
        self.assertEqual(Author.objects.values_list(Cast('age', models.TextField()), flat=True).get(), '1')
