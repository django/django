from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import (
    CompositeField,
    Count,
    F,
    Func,
    IntegerField,
    JSONField,
    Q,
    TextField,
    Value,
)
from django.db.models.functions import Abs, Upper
from django.db.models.lookups import GreaterThan
from django.test.utils import CaptureQueriesContext, register_lookup

from . import PostgreSQLSimpleTestCase, PostgreSQLTestCase
from .models import AggregateTestModel


class GenerateSeries(Func):
    function = "generate_series"
    output_field = IntegerField()
    set_returning = True
    table_source = True


class SelectListGenerateSeries(Func):
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
    table_source = True


class NestedUnnest(Func):
    function = "unnest"
    output_field = CompositeField(
        number=IntegerField(),
        item=CompositeField(
            key=TextField(),
            value=TextField(),
        ),
    )
    set_returning = True
    table_source = True


class SetReturningFunctionTests(PostgreSQLSimpleTestCase):
    def test_annotate_keeps_select_list_behavior(self):
        queryset = AggregateTestModel.objects.annotate(
            number=SelectListGenerateSeries(1, 2)
        ).values("number")
        sql, params = queryset.query.sql_with_params()

        self.assertIn('generate_series(%s, %s) AS "number"', sql)
        self.assertNotIn("CROSS JOIN", sql)
        self.assertEqual(params, (1, 2))

    def test_set_returning_alias_is_not_a_table_source(self):
        queryset = (
            AggregateTestModel.objects.alias(number=SelectListGenerateSeries(1, 2))
            .annotate(result=F("number"))
            .values("result")
        )
        sql, params = queryset.query.sql_with_params()

        self.assertIn('generate_series(%s, %s) AS "result"', sql)
        self.assertNotIn("CROSS JOIN", sql)
        self.assertEqual(params, (1, 2))

    def test_table_source_annotation_is_added_to_from_clause(self):
        queryset = AggregateTestModel.objects.annotate(
            number=GenerateSeries(1, 2)
        ).values("number")
        sql, params = queryset.query.sql_with_params()

        self.assertIn('"number"."number" AS "number"', sql)
        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertEqual(params, (1, 2))

    def test_table_source_alias_rejects_lookup_separator(self):
        msg = (
            "Table source alias 'some__alias' cannot contain the lookup "
            "separator '__'."
        )
        for method in ("alias", "annotate"):
            with self.subTest(method), self.assertRaisesMessage(ValueError, msg):
                getattr(AggregateTestModel.objects, method)(
                    **{"some__alias": GenerateSeries(1, 2)}
                )

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

    def test_nested_composite_columns(self):
        results = (
            AggregateTestModel.objects.filter(char_field="first")
            .alias(
                row=NestedUnnest(
                    Value([1, 2], output_field=ArrayField(IntegerField())),
                    Value(
                        ["color", "size"],
                        output_field=ArrayField(TextField()),
                    ),
                    Value(
                        ["blue", "large"],
                        output_field=ArrayField(TextField()),
                    ),
                )
            )
            .order_by("row__number")
            .values_list(
                "row__number",
                "row__item__key",
                "row__item__value",
            )
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn(
            'AS "row"("number", "item__key", "item__value")',
            sql,
        )
        self.assertSequenceEqual(
            list(results),
            [
                (1, "color", "blue"),
                (2, "size", "large"),
            ],
        )

    def test_q_or_keeps_selected_composite_column_required(self):
        results = (
            AggregateTestModel.objects.alias(item=JsonbEach("json_field"))
            .values_list("item__key", flat=True)
            .filter(Q(char_field="empty") | Q(item__key="missing"))
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), [])

    def test_q_or_then_values_keeps_composite_column_required(self):
        AggregateTestModel.objects.create(char_field="keep", json_field={})

        results = (
            AggregateTestModel.objects.alias(item=JsonbEach("json_field"))
            .filter(Q(char_field="keep") | Q(item__key="missing"))
            .values_list("char_field", "item__key")
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), [])

    def test_filter_composite_tuple(self):
        queryset = AggregateTestModel.objects.alias(item=JsonbEach("json_field"))

        for value, expected in [
            (("color", "blue"), ["first"]),
            (("color", "red"), ["second"]),
            (("color", "green"), []),
            (("size", "blue"), []),
        ]:
            with self.subTest(value=value):
                results = queryset.filter(item=value).values_list(
                    "char_field", flat=True
                )
                sql, _ = results.query.sql_with_params()

                self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
                self.assertSequenceEqual(list(results), expected)

    def test_filter_composite_tuple_reuses_join(self):
        results = (
            AggregateTestModel.objects.alias(item=JsonbEach("json_field"))
            .filter(item__key="color")
            .filter(item=("color", "blue"))
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertSequenceEqual(list(results), ["first"])

    def test_composite_column_transform(self):
        with register_lookup(TextField, Upper):
            results = (
                AggregateTestModel.objects.filter(char_field="second")
                .alias(item=JsonbEach("json_field"))
                .annotate(key=F("item__key__upper"))
                .order_by("key")
                .values_list("key", flat=True)
            )
            sql, _ = results.query.sql_with_params()

            self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
            self.assertEqual(sql.count("jsonb_each"), 1)
            self.assertIn('UPPER("item"."key") AS "key"', sql)
            self.assertSequenceEqual(list(results), ["COLOR", "COUNT", "SIZE"])

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

    def test_q_or_then_aggregate_keeps_table_source_required(self):
        AggregateTestModel.objects.create(char_field="keep")
        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 0)).filter(
            Q(char_field="keep") | Q(number=1)
        )

        with CaptureQueriesContext(connection) as captured_queries:
            result = queryset.aggregate(total=Count("number"))

        self.assertIn("CROSS JOIN LATERAL", captured_queries[0]["sql"])
        self.assertNotIn("LEFT OUTER JOIN LATERAL", captured_queries[0]["sql"])
        self.assertEqual(result, {"total": 0})

    def test_q_or_then_unrelated_aggregate_keeps_table_source_optional(self):
        AggregateTestModel.objects.create(char_field="keep")
        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 0)).filter(
            Q(char_field="keep") | Q(number=1)
        )

        with CaptureQueriesContext(connection) as captured_queries:
            result = queryset.aggregate(total=Count("pk"))

        self.assertIn("LEFT OUTER JOIN LATERAL", captured_queries[0]["sql"])
        self.assertNotIn("CROSS JOIN LATERAL", captured_queries[0]["sql"])
        self.assertEqual(result, {"total": 1})


class MultipleSetReturningFunctionExecutionTests(PostgreSQLTestCase):
    def test_or_promotes_dependent_function_chain(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )

        results = (
            AggregateTestModel.objects.alias(
                upper_bound=GenerateSeries(1, 0),
                number=GenerateSeries(1, F("upper_bound")),
            )
            .filter(Q(char_field="keep") | Q(number=1))
            .order_by("char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("LEFT OUTER JOIN LATERAL"), 2)
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["keep"])

    def test_function_uses_previous_function_column(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="empty", integer_field=0),
                AggregateTestModel(char_field="first", integer_field=2),
                AggregateTestModel(char_field="second", integer_field=3),
            ]
        )

        results = (
            AggregateTestModel.objects.alias(
                upper_bound=GenerateSeries(1, "integer_field"),
                number=GenerateSeries(1, F("upper_bound")),
            )
            .annotate(
                upper_bound_value=F("upper_bound"),
                number_value=F("number"),
            )
            .order_by("char_field", "upper_bound_value", "number_value")
            .values_list("char_field", "upper_bound_value", "number_value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 2)
        self.assertEqual(sql.count("generate_series"), 2)
        self.assertIn(
            'generate_series(%s, "upper_bound"."upper_bound")',
            sql,
        )
        self.assertSequenceEqual(
            list(results),
            [
                ("first", 1, 1),
                ("first", 2, 1),
                ("first", 2, 2),
                ("second", 1, 1),
                ("second", 2, 1),
                ("second", 2, 2),
                ("second", 3, 1),
                ("second", 3, 2),
                ("second", 3, 3),
            ],
        )

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
    def test_update_rejects_table_source_reference(self):
        obj = AggregateTestModel.objects.create(integer_field=0)

        msg = "Joined field references are not permitted in this query"
        with self.assertRaisesMessage(FieldError, msg):
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 2)).update(
                integer_field=F("number")
            )

        obj.refresh_from_db()
        self.assertEqual(obj.integer_field, 0)

    def test_update_rejects_annotated_table_source_reference(self):
        obj = AggregateTestModel.objects.create(integer_field=0)

        msg = "Joined field references are not permitted in this query"
        with self.assertRaisesMessage(FieldError, msg):
            AggregateTestModel.objects.annotate(number=GenerateSeries(1, 2)).update(
                integer_field=F("number")
            )

        obj.refresh_from_db()
        self.assertEqual(obj.integer_field, 0)

    def test_update_rejects_table_source_column_reference(self):
        obj = AggregateTestModel.objects.create(
            char_field="original",
            json_field={"color": "blue"},
        )

        msg = "Joined field references are not permitted in this query"
        with self.assertRaisesMessage(FieldError, msg):
            AggregateTestModel.objects.alias(item=JsonbEach("json_field")).update(
                char_field=F("item__key")
            )

        obj.refresh_from_db()
        self.assertEqual(obj.char_field, "original")

    def test_and_combines_table_source_queryset(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )
        left = AggregateTestModel.objects.filter(char_field="keep")
        right = AggregateTestModel.objects.alias(number=GenerateSeries(1, 2)).filter(
            number=2
        )

        results = (left & right).values_list("char_field", flat=True)
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("generate_series"), 1)
        self.assertSequenceEqual(list(results), ["keep"])

    def test_or_preserves_rows_when_table_source_is_empty(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )
        matching = AggregateTestModel.objects.filter(char_field="keep")
        empty_table_source = AggregateTestModel.objects.alias(
            number=GenerateSeries(1, 0)
        ).filter(number=1)

        for order, queryset in [
            ("table source on left", empty_table_source | matching),
            ("table source on right", matching | empty_table_source),
        ]:
            with self.subTest(order):
                results = queryset.order_by("char_field").values_list(
                    "char_field", flat=True
                )
                sql, _ = results.query.sql_with_params()

                self.assertEqual(sql.count("generate_series"), 1)
                self.assertSequenceEqual(list(results), ["keep"])

    def test_or_reuses_same_table_source(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="first"),
                AggregateTestModel(char_field="second"),
            ]
        )
        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
        results = (
            (queryset.filter(number=1) | queryset.filter(number=3))
            .annotate(result=F("number"))
            .order_by("char_field", "result")
            .values_list("char_field", "result")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("generate_series"), 1)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(
            list(results),
            [
                ("first", 1),
                ("first", 3),
                ("second", 1),
                ("second", 3),
            ],
        )

    def test_or_keeps_different_table_sources(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="first"),
                AggregateTestModel(char_field="second"),
            ]
        )
        left = AggregateTestModel.objects.alias(number=GenerateSeries(1, 1)).filter(
            number=99
        )
        right = AggregateTestModel.objects.alias(number=GenerateSeries(7, 7)).filter(
            number=7
        )

        results = (
            (left | right).order_by("char_field").values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("generate_series"), 2)
        self.assertEqual(sql.count("LEFT OUTER JOIN LATERAL"), 2)
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["first", "second"])

    def test_q_or_preserves_rows_when_table_source_is_empty(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )
        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 0))
            .filter(Q(char_field="keep") | Q(number=1))
            .order_by("char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["keep"])

    def test_q_or_with_conditional_expression_preserves_rows(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )
        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 0))
            .filter(
                Q(char_field="keep") | Q(GreaterThan(F("number"), 0)),
            )
            .order_by("char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["keep"])

    def test_q_or_keeps_selected_table_source_required(self):
        AggregateTestModel.objects.create(char_field="keep")

        results = (
            AggregateTestModel.objects.annotate(number=GenerateSeries(1, 0))
            .filter(Q(char_field="keep") | Q(number=1))
            .values_list("char_field", "number")
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), [])

    def test_q_or_then_annotation_keeps_table_source_required(self):
        AggregateTestModel.objects.create(char_field="keep")

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 0))
            .filter(Q(char_field="keep") | Q(number=1))
            .annotate(result=F("number"))
            .values_list("char_field", "result")
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), [])

    def test_q_or_then_ordering_keeps_table_source_required(self):
        AggregateTestModel.objects.create(char_field="keep")

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 0))
            .filter(Q(char_field="keep") | Q(number=1))
            .order_by("number")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), [])

    def test_replaced_ordering_keeps_table_source_optional(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 0))
            .filter(Q(char_field="keep") | Q(number=1))
            .order_by("number")
            .order_by("char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["keep"])

    def test_q_or_keeps_previously_filtered_table_source_required(self):
        AggregateTestModel.objects.create(char_field="keep")

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 0))
            .filter(number=1)
            .filter(Q(char_field="keep") | Q(number=2))
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), [])

    def test_required_filter_demotes_optional_table_source(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="keep"),
                AggregateTestModel(char_field="discard"),
            ]
        )
        optional = AggregateTestModel.objects.alias(number=GenerateSeries(1, 2)).filter(
            Q(char_field="keep") | Q(number=1)
        )
        optional_sql, _ = optional.query.sql_with_params()

        self.assertIn("LEFT OUTER JOIN LATERAL", optional_sql)

        results = (
            optional.filter(number=2)
            .order_by("char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("CROSS JOIN LATERAL", sql)
        self.assertNotIn("LEFT OUTER JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["keep"])

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

    def test_scalar_function_transform(self):
        AggregateTestModel.objects.create()

        with register_lookup(IntegerField, Abs):
            results = (
                AggregateTestModel.objects.alias(number=GenerateSeries(-2, 2))
                .annotate(result=F("number__abs"))
                .order_by("number")
                .values_list("result", flat=True)
            )
            sql, _ = results.query.sql_with_params()

            self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
            self.assertEqual(sql.count("generate_series"), 1)
            self.assertIn('ABS("number"."number") AS "result"', sql)
            self.assertSequenceEqual(list(results), [2, 1, 0, 1, 2])

    def test_chained_operations_reuse_function_join(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
            .filter(number__gt=1)
            .annotate(result=F("number"))
            .order_by("result")
            .values("result")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertEqual(sql.count("generate_series"), 1)
        self.assertSequenceEqual(
            list(results),
            [
                {"result": 2},
                {"result": 3},
            ],
        )

    def test_reassigned_materialized_alias_uses_new_function(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 2))
            .filter(number=1)
            .alias(number=GenerateSeries(7, 8))
            .annotate(result=F("number"))
            .order_by("result")
            .values_list("result", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertSequenceEqual(list(results), [7, 8])
        self.assertEqual(sql.count("generate_series"), 2)

    def test_reassigned_selected_alias_discards_old_function(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.annotate(number=GenerateSeries(1, 2))
            .alias(number=GenerateSeries(7, 8))
            .annotate(result=F("number"))
            .order_by("result")
            .values_list("result", flat=True)
        )
        sql, params = results.query.sql_with_params()

        self.assertEqual(sql.count("generate_series"), 1)
        self.assertEqual(params, (7, 8))
        self.assertSequenceEqual(list(results), [7, 8])

    def test_reassigned_selected_alias_keeps_filtered_function(self):
        AggregateTestModel.objects.create()

        results = (
            AggregateTestModel.objects.annotate(number=GenerateSeries(1, 2))
            .filter(number=1)
            .alias(number=GenerateSeries(7, 8))
            .annotate(result=F("number"))
            .order_by("result")
            .values_list("result", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("generate_series"), 2)
        self.assertSequenceEqual(list(results), [7, 8])

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

    def test_ordering_only_materializes_function(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="first"),
                AggregateTestModel(char_field="second"),
            ]
        )

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
            .order_by("-number", "char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()
        select_clause = sql.split(" FROM ", 1)[0]

        self.assertEqual(sql.count("CROSS JOIN LATERAL"), 1)
        self.assertEqual(sql.count("generate_series"), 1)
        self.assertNotIn('"number"."number"', select_clause)
        self.assertIn('ORDER BY "number"."number" DESC', sql)
        self.assertSequenceEqual(
            list(results),
            ["first", "second", "first", "second", "first", "second"],
        )

    def test_replaced_ordering_does_not_materialize_function(self):
        AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(char_field="first"),
                AggregateTestModel(char_field="second"),
            ]
        )

        results = (
            AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
            .order_by("number")
            .order_by("char_field")
            .values_list("char_field", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertNotIn("generate_series", sql)
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertSequenceEqual(list(results), ["first", "second"])

    def test_count_keeps_selected_table_source_required(self):
        AggregateTestModel.objects.create()
        queryset = AggregateTestModel.objects.annotate(number=GenerateSeries(1, 0))

        with CaptureQueriesContext(connection) as captured_queries:
            result = queryset.count()

        self.assertIn("CROSS JOIN LATERAL", captured_queries[0]["sql"])
        self.assertNotIn("LEFT OUTER JOIN LATERAL", captured_queries[0]["sql"])
        self.assertEqual(result, 0)

    def test_count_does_not_materialize_unused_table_source(self):
        AggregateTestModel.objects.create()
        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))

        with CaptureQueriesContext(connection) as captured_queries:
            result = queryset.count()

        self.assertNotIn("generate_series", captured_queries[0]["sql"])
        self.assertNotIn("CROSS JOIN LATERAL", captured_queries[0]["sql"])
        self.assertEqual(result, 1)

    def test_exists_keeps_selected_table_source_required(self):
        AggregateTestModel.objects.create()
        queryset = AggregateTestModel.objects.annotate(number=GenerateSeries(1, 0))

        with CaptureQueriesContext(connection) as captured_queries:
            result = queryset.exists()

        self.assertIn("CROSS JOIN LATERAL", captured_queries[0]["sql"])
        self.assertNotIn("LEFT OUTER JOIN LATERAL", captured_queries[0]["sql"])
        self.assertIs(result, False)

    def test_exists_does_not_materialize_unused_table_source(self):
        AggregateTestModel.objects.create()
        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))

        with CaptureQueriesContext(connection) as captured_queries:
            result = queryset.exists()

        self.assertNotIn("generate_series", captured_queries[0]["sql"])
        self.assertNotIn("CROSS JOIN LATERAL", captured_queries[0]["sql"])
        self.assertIs(result, True)

    def test_unused_scalar_function_is_not_materialized(self):
        obj = AggregateTestModel.objects.create()

        queryset = AggregateTestModel.objects.alias(number=GenerateSeries(1, 3))
        sql, _ = queryset.query.sql_with_params()

        self.assertNotIn("generate_series", sql)
        self.assertSequenceEqual(list(queryset), [obj])
