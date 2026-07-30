from django.db.models import (
    CompositeField,
    Count,
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
    def test_annotate_keeps_select_list_behavior(self):
        queryset = AggregateTestModel.objects.annotate(
            number=GenerateSeries(1, 2)
        ).values("number")
        sql, params = queryset.query.sql_with_params()

        self.assertIn('generate_series(%s, %s) AS "number"', sql)
        self.assertNotIn("CROSS JOIN", sql)
        self.assertEqual(params, (1, 2))

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


class CompositeSetReturningFunctionExecutionTests(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="empty", json_field={}),
                AggregateTestModel(char_field="null", json_field=None),
                AggregateTestModel(
                    char_field="first",
                    json_field={
                        "active": True,
                        "color": "blue",
                        "count": 2,
                        "metadata": {"region": "eu"},
                        "nothing": None,
                        "size": "large",
                        "tags": ["django", "orm"],
                    },
                ),
                AggregateTestModel(
                    char_field="second",
                    json_field={
                        "color": "red",
                        "count": 0,
                        "size": "small",
                    },
                ),
            ]
        )

    def test_filter_composite_columns(self):
        results = (
            AggregateTestModel.objects.alias(item=JsonbEach("json_field"))
            .filter(item__key="size", item__value="large")
            .values_list("char_field", "item__key", "item__value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertSequenceEqual(list(results), [("first", "size", "large")])

    def test_returns_composite_columns(self):
        results = (
            AggregateTestModel.objects.alias(item=JsonbEach("json_field"))
            .order_by("char_field", "item__key")
            .values_list("char_field", "item__key", "item__value")
        )

        self.assertSequenceEqual(
            list(results),
            [
                ("first", "active", True),
                ("first", "color", "blue"),
                ("first", "count", 2),
                ("first", "metadata", {"region": "eu"}),
                ("first", "nothing", None),
                ("first", "size", "large"),
                ("first", "tags", ["django", "orm"]),
                ("second", "color", "red"),
                ("second", "count", 0),
                ("second", "size", "small"),
            ],
        )


class CorrelatedSetReturningFunctionExecutionTests(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="empty-null", integer_field=None),
                AggregateTestModel(char_field="empty-zero", integer_field=0),
                AggregateTestModel(char_field="first", integer_field=2),
                AggregateTestModel(char_field="second", integer_field=3),
            ]
        )

    def test_function_uses_each_outer_row(self):
        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, "integer_field"))
            .annotate(result=F("number"))
            .order_by("char_field", "result")
            .values_list("char_field", "result")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertSequenceEqual(
            list(results),
            [
                ("first", 1),
                ("first", 2),
                ("second", 1),
                ("second", 2),
                ("second", 3),
            ],
        )

    def test_aggregate_over_function_column(self):
        result = AggregateTestModel.objects.alias(
            number=GenerateSeries(1, "integer_field")
        ).aggregate(total=Count("number"))

        self.assertEqual(result, {"total": 5})


class MultipleSetReturningFunctionExecutionTests(PostgreSQLTestCase):
    def test_multiple_functions_expand_independently(self):
        AggregateTestModel.objects.create(json_field={"color": "blue", "size": "large"})

        results = (
            AggregateTestModel.objects.alias(
                number=GenerateSeries(1, 2),
                item=JsonbEach("json_field"),
            )
            .annotate(number_value=F("number"))
            .order_by("number_value", "item__key")
            .values_list("number_value", "item__key", "item__value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 2)
        self.assertSequenceEqual(
            list(results),
            [
                (1, "color", "blue"),
                (1, "size", "large"),
                (2, "color", "blue"),
                (2, "size", "large"),
            ],
        )


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
