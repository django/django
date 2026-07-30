from django.db.models import (
    CompositeField,
    F,
    Func,
    IntegerField,
    JSONField,
    TextField,
)

from . import PostgreSQLSimpleTestCase, PostgreSQLTestCase
from .models import AggregateTestModel


class GenerateSeries(Func):
    function = "generate_series"
    output_field = IntegerField()
    set_returning = True


class JsonbEach(Func):
    function = "jsonb_each"
    output_field = CompositeField(
        key=TextField(),
        value=JSONField(),
    )
    set_returning = True


class SetReturningFunctionTests(PostgreSQLSimpleTestCase):
    def test_scalar_function_is_added_to_from_clause(self):
        queryset = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 2))
            .annotate(result=F("number"))
            .values("result")
        )
        sql, params = queryset.query.sql_with_params()

        self.assertIn('"number"."number" AS "result"', sql)
        self.assertIn(
            'FROM "postgres_tests_aggregatetestmodel" '
            "CROSS JOIN LATERAL generate_series",
            sql,
        )
        self.assertIn('AS "number"("number")', sql)
        self.assertEqual(params, (1, 2))

    def test_composite_function_is_added_to_from_clause(self):
        queryset = AggregateTestModel.objects.alias(
            item=JsonbEach("json_field")
        ).values("item__key", "item__value")
        sql, params = queryset.query.sql_with_params()

        self.assertIn('"item"."key" AS "item__key"', sql)
        self.assertIn('"item"."value" AS "item__value"', sql)
        self.assertIn("CROSS JOIN LATERAL jsonb_each", sql)
        self.assertIn('AS "item"("key", "value")', sql)
        self.assertEqual(params, ())


class SetReturningFunctionExecutionTests(PostgreSQLTestCase):
    def test_scalar_function_returns_rows(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 2))
            .annotate(result=F("number"))
            .order_by("result")
            .values_list("result", flat=True)
        )

        self.assertSequenceEqual(list(results), [1, 2])

    def test_scalar_function_filter(self):
        obj = AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
            .filter(number__gt=1)
            .values_list("pk", flat=True)
        )

        self.assertSequenceEqual(list(results), [obj.pk, obj.pk])

    def test_scalar_function_join_is_reused(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
            .filter(number__gt=1)
            .annotate(result=F("number"))
            .order_by("result")
            .values_list("result", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertSequenceEqual(list(results), [2, 3])

    def test_scalar_function_ordering(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
            .annotate(result=F("number"))
            .order_by("-number")
            .values_list("result", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn('ORDER BY "number"."number" DESC', sql)
        self.assertSequenceEqual(list(results), [3, 2, 1])

    def test_unused_scalar_function_is_not_materialized(self):
        obj = AggregateTestModel.objects.create()

        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
        sql, _ = queryset.query.sql_with_params()

        self.assertNotIn("generate_series", sql)
        self.assertSequenceEqual(list(queryset), [obj])
