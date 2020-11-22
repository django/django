from datetime import datetime
from math import pi
from unittest import skipIf, skipUnless

from django.core import checks
from django.db import connection
from django.db.models import F, FloatField, Value
from django.db.models.expressions import (
    Expression, ExpressionList, ExpressionWrapper, Func, RawSQL,
)
from django.db.models.functions import Coalesce, Collate, Pi
from django.test import TestCase

from .models import (
    Article, DBArticle, DBDefaults, DBDefaultsFK, DBDefaultsFunction,
    DBDefaultsPK,
)


class DefaultTests(TestCase):
    def test_field_defaults(self):
        a = Article()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((now - a.pub_date).seconds, 5)

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_field_database_defaults_postgres(self):
        a = DBArticle()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((a.pub_date - now).seconds, 5)

    @skipUnless(connection.vendor == 'mysql', 'MySQL test')
    def test_field_database_defaults_mysql(self):
        a = DBArticle()
        now = datetime.utcnow()
        a.save()
        a.refresh_from_db()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((a.pub_date - now).seconds, 5)

    @skipUnless(connection.vendor == 'sqlite', 'Sqlite test')
    def test_field_database_defaults_sqlite(self):
        a = DBArticle()
        now = datetime.utcnow()
        a.save()
        a.refresh_from_db()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((now - a.pub_date).seconds, 5)

    def test_bulk_create_all_db_defaults(self):
        articles = [DBArticle(), DBArticle()]
        DBArticle.objects.bulk_create(articles)

        expected_headlines = ['Default headline', 'Default headline']
        headlines = DBArticle.objects.values_list('headline', flat=True)
        self.assertCountEqual(headlines, expected_headlines)

    def test_bulk_create_all_db_defaults_one_field(self):
        articles = [DBArticle(pub_date=datetime.now()), DBArticle(pub_date=datetime.now())]
        DBArticle.objects.bulk_create(articles)

        expected_headlines = ['Default headline', 'Default headline']
        headlines = DBArticle.objects.values_list('headline', flat=True)
        self.assertCountEqual(headlines, expected_headlines)

    def test_bulk_create_mixed_db_defaults(self):
        articles = [DBArticle(), DBArticle(headline='Something else')]
        DBArticle.objects.bulk_create(articles)

        expected_headlines = ['Default headline', 'Something else']
        headlines = DBArticle.objects.values_list('headline', flat=True)
        self.assertCountEqual(headlines, expected_headlines)

    @skipUnless(
        connection.features.supports_functions_in_defaults,
        'MySQL before 8.0.13 does not support function defaults.',
    )
    def test_bulk_create_mixed_db_defaults_function(self):
        instances = [DBDefaultsFunction(), DBDefaultsFunction(year=2000)]
        DBDefaultsFunction.objects.bulk_create(instances)

        expected_years = [2000, datetime.now().year]
        years = DBDefaultsFunction.objects.values_list('year', flat=True)
        self.assertCountEqual(years, expected_years)

    def test_null_db_default(self):
        m = DBDefaults.objects.create()
        if not connection.features.can_return_columns_from_insert:
            m.refresh_from_db()
        self.assertEqual(m.null, 1.1)

        m2 = DBDefaults.objects.create(null=None)
        self.assertIsNone(m2.null)

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_both_default_postgres(self):
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO field_defaults_dbdefaults DEFAULT VALUES')
        m = DBDefaults.objects.get()
        self.assertEqual(m.both, 2)

        m2 = DBDefaults.objects.create()
        self.assertEqual(m2.both, 1)

    @skipUnless(connection.vendor == 'mysql', 'MySQL test')
    def test_both_default_mysql(self):
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO field_defaults_dbdefaults () VALUES ()')
        m = DBDefaults.objects.get()
        self.assertEqual(m.both, 2)

        m2 = DBDefaults.objects.create()
        self.assertEqual(m2.both, 1)

    @skipUnless(connection.vendor == 'sqlite', 'Sqlite test')
    def test_both_default_sqlite(self):
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO field_defaults_dbdefaults ("null") VALUES (1)')
        m = DBDefaults.objects.get()
        self.assertEqual(m.both, 2)

        m2 = DBDefaults.objects.create()
        self.assertEqual(m2.both, 1)

    @skipUnless(
        connection.features.supports_functions_in_defaults,
        'MySQL before 8.0.13 does not support function defaults.',
    )
    def test_db_default_function(self):
        m = DBDefaultsFunction.objects.create()
        if not connection.features.can_return_columns_from_insert:
            m.refresh_from_db()
        self.assertAlmostEqual(m.number, pi)
        self.assertEqual(m.year, datetime.now().year)
        self.assertAlmostEqual(m.added, pi + 4.5)
        self.assertEqual(m.multiple_subfunctions, 4.5)

    @skipIf(
        connection.features.supports_functions_in_defaults,
        'MySQL before 8.0.13 does not support function defaults.',
    )
    def test_db_default_function_invalid(self):
        field = FloatField(name='field', db_default=Pi())

        errors = field.check()

        expected_error = checks.Error(
            msg=f"MySQL {connection.mysql_version} doesn't support functions as database defaults.",
            obj=field,
            id='fields.E011',
        )
        self.assertEqual(errors, [expected_error])

    def test_db_default_expression_invalid(self):
        expression = F('field_name')
        field = FloatField(name='field', db_default=expression)

        errors = field.check()

        expected_error = checks.Error(
            msg=f'{expression} is not a valid database default.',
            obj=field,
            id='fields.E011',
        )
        self.assertEqual(errors, [expected_error])

    def test_db_default_combined_invalid(self):
        expression = Value(4.5) + F('field_name')
        field = FloatField(name='field', db_default=expression)

        errors = field.check()

        expected_error = checks.Error(
            msg=f'{expression} is not a valid database default.',
            obj=field,
            id='fields.E011',
        )
        self.assertEqual(errors, [expected_error])

    def test_db_default_function_arguments_invalid(self):
        expression = Coalesce(Value(4.5), F('field_name'))
        field = FloatField(name='field', db_default=expression)

        errors = field.check()

        expected_error = checks.Error(
            msg=f'{expression} is not a valid database default.',
            obj=field,
            id='fields.E011',
        )
        self.assertEqual(errors, [expected_error])

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_pk_db_default(self):
        m = DBDefaultsPK.objects.create()
        self.assertEqual(m.pk, 'en')
        self.assertEqual(m.language_code, 'en')

        m2 = DBDefaultsPK.objects.create(language_code='de')
        self.assertEqual(m2.pk, 'de')
        self.assertEqual(m2.language_code, 'de')

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_foreign_key_db_default(self):
        m = DBDefaultsPK.objects.create(language_code='fr')
        r = DBDefaultsFK.objects.create()
        self.assertEqual(r.language_code, m)

        m2 = DBDefaultsPK.objects.create()
        r2 = DBDefaultsFK.objects.create(language_code=m2)
        self.assertEqual(r2.language_code, m2)


class AllowedDefaultTests(TestCase):
    def test_value(self):
        value = Value(10)
        self.assertTrue(value.allowed_default)

    def test_func_allowed(self):
        class Max(Func):
            function = 'MAX'

        maximum = Max(1, 2)
        self.assertTrue(maximum.allowed_default)

    def test_func_disallowed(self):
        class Max(Func):
            function = 'MAX'

        maximum = Max(F('count'), 1)
        self.assertFalse(maximum.allowed_default)

    def test_raw_sql(self):
        now = RawSQL('Now()', ())
        self.assertTrue(now.allowed_default)

    def test_f(self):
        field = F('field')
        self.assertFalse(field.allowed_default)

    def test_expression(self):
        expression = Expression()
        self.assertFalse(expression.allowed_default)

    def test_combined_expression_allowed(self):
        combined = Value(10) + Value(7)
        self.assertTrue(combined.allowed_default)

    def test_combined_expression_disallowed(self):
        combined = Value(10) + F('count')
        self.assertFalse(combined.allowed_default)

    def test_expression_list_allowed(self):
        expressions = ExpressionList(Value(1), Value(2))
        self.assertTrue(expressions.allowed_default)

    def test_expression_list_disallowed(self):
        expressions = ExpressionList(F('count'), Value(2))
        self.assertFalse(expressions.allowed_default)

    def test_expression_wrapper_allowed(self):
        expression = ExpressionWrapper(Value(1), output_field=FloatField())
        self.assertTrue(expression.allowed_default)

    def test_expression_wrapper_disallowed(self):
        expression = ExpressionWrapper(F('count'), output_field=FloatField())
        self.assertFalse(expression.allowed_default)

    def test_collate_disallowed(self):
        collate = Collate(Value('John'), 'nocase')
        self.assertFalse(collate.allowed_default)
