import unittest

from django.db import connection
from django.db.models import (
    CompositeField,
    F,
    Func,
    IntegerField,
    JSONField,
    Q,
    TextField,
    Value,
)
from django.test import TestCase

from .models import JSONFieldNullable, Node


class JsonEach(Func):
    function = "json_each"
    output_field = TextField(db_column="value")
    set_returning = True
    table_source = True


class JsonEachRow(Func):
    function = "json_each"
    output_field = CompositeField(
        key=IntegerField(db_column="key"),
        value=TextField(db_column="value"),
    )
    set_returning = True
    table_source = True


class JsonEachObjectRow(JsonEachRow):
    output_field = CompositeField(
        key=TextField(db_column="key"),
        value=TextField(db_column="value"),
    )


class JsonEachTypeRow(JsonEachRow):
    output_field = CompositeField(
        key=IntegerField(db_column="key"),
        json_type=TextField(db_column="type"),
    )


class JsonTableArrayRow(Func):
    function = "JSON_TABLE"
    output_field = CompositeField(
        position=IntegerField(db_column="position"),
        value=TextField(db_column="value"),
    )
    set_returning = True
    table_source = True

    def _as_json_table(
        self,
        compiler,
        connection,
        value_type,
        expression_template="%(expressions)s",
        **extra_context,
    ):
        qn = connection.ops.quote_name
        template = (
            f"%(function)s({expression_template}, '$[*]' COLUMNS ("
            f"{qn('position')} FOR ORDINALITY, "
            f"{qn('value')} {value_type} PATH '$'))"
        )
        return super().as_sql(
            compiler,
            connection,
            template=template,
            **extra_context,
        )

    def as_mysql(self, compiler, connection, **extra_context):
        expression_template = "%(expressions)s"
        if not connection.mysql_is_mariadb:
            # MySQL can lose the JSON type when a column comes from a derived
            # table. Normalize the input before passing it to JSON_TABLE().
            expression_template = "JSON_EXTRACT(%(expressions)s, '$')"
        return self._as_json_table(
            compiler,
            connection,
            "VARCHAR(100)",
            expression_template=expression_template,
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        return self._as_json_table(
            compiler,
            connection,
            "VARCHAR2(100)",
            **extra_context,
        )


class JsonTableArrayValue(JsonTableArrayRow):
    output_field = TextField(db_column="value")


class SetReturningFunctionOuterJoinMixin:
    table_source_class = None

    def test_or_preserves_rows_when_table_source_is_empty(self):
        results = (
            JSONFieldNullable.objects.alias(
                element=self.table_source_class("json_field")
            )
            .filter(Q(pk=self.empty.pk) | Q(element="not-present"))
            .values_list("pk", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertIn("LEFT OUTER JOIN", sql)
        self.assertNotIn("CROSS JOIN", sql)
        self.assertNotIn("LATERAL", sql)
        self.assertSequenceEqual(list(results), [self.empty.pk])


@unittest.skipUnless(connection.vendor == "sqlite", "SQLite tests")
class SQLiteSetReturningFunctionTests(SetReturningFunctionOuterJoinMixin, TestCase):
    table_source_class = JsonEach

    @classmethod
    def setUpTestData(cls):
        cls.populated = JSONFieldNullable.objects.create(
            json_field=["beta", "alpha", "beta"]
        )
        cls.empty = JSONFieldNullable.objects.create(json_field=[])
        JSONFieldNullable.objects.create(json_field=None)

    def test_table_source_alias_does_not_replace_table_join(self):
        grandparent = Node.objects.create(num=1)
        parent = Node.objects.create(num=2, parent=grandparent)
        child = Node.objects.create(num=3, parent=parent)

        results = (
            Node.objects.filter(parent__parent__num=grandparent.num)
            .alias(
                T2=JsonEach(Value(["match"], output_field=JSONField())),
            )
            .filter(T2="match")
            .values_list("pk", flat=True)
        )

        self.assertSequenceEqual(list(results), [child.pk])

    def test_json_each_composite_columns(self):
        results = (
            JSONFieldNullable.objects.alias(element=JsonEachRow("json_field"))
            .order_by("pk", "element__key")
            .values_list("pk", "element__key", "element__value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN"), 1)
        self.assertNotIn("LATERAL", sql)
        self.assertSequenceEqual(
            list(results),
            [
                (self.populated.pk, 0, "beta"),
                (self.populated.pk, 1, "alpha"),
                (self.populated.pk, 2, "beta"),
            ],
        )

    def test_json_each_composite_filter(self):
        results = (
            JSONFieldNullable.objects.alias(element=JsonEachRow("json_field"))
            .filter(element__key__gte=1, element__value="beta")
            .values_list("element__key", "element__value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN"), 1)
        self.assertSequenceEqual(list(results), [(2, "beta")])

    def test_json_each_mixed_json_types(self):
        source = JSONFieldNullable.objects.create(
            json_field=[
                None,
                True,
                False,
                7,
                2.5,
                "text",
                [1],
                {"name": "Django"},
            ]
        )

        results = (
            JSONFieldNullable.objects.filter(pk=source.pk)
            .alias(element=JsonEachTypeRow("json_field"))
            .order_by("element__key")
            .values_list("element__key", "element__json_type")
        )

        self.assertSequenceEqual(
            list(results),
            [
                (0, "null"),
                (1, "true"),
                (2, "false"),
                (3, "integer"),
                (4, "real"),
                (5, "text"),
                (6, "array"),
                (7, "object"),
            ],
        )

    def test_json_each_object_members(self):
        source = JSONFieldNullable.objects.create(
            json_field={
                "beta": "second",
                "alpha": "first",
                "nothing": None,
            }
        )

        results = (
            JSONFieldNullable.objects.filter(pk=source.pk)
            .alias(member=JsonEachObjectRow("json_field"))
            .order_by("member__key")
            .values_list("member__key", "member__value")
        )

        self.assertSequenceEqual(
            list(results),
            [
                ("alpha", "first"),
                ("beta", "second"),
                ("nothing", None),
            ],
        )

    def test_json_each_returns_array_elements(self):
        results = (
            JSONFieldNullable.objects.alias(element=JsonEach("json_field"))
            .annotate(value=F("element"))
            .order_by("pk", "value")
            .values_list("pk", "value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN"), 1)
        self.assertNotIn("LATERAL", sql)
        self.assertSequenceEqual(
            list(results),
            [
                (self.populated.pk, "alpha"),
                (self.populated.pk, "beta"),
                (self.populated.pk, "beta"),
            ],
        )


@unittest.skipUnless(
    connection.vendor in {"mysql", "oracle"},
    "MySQL, MariaDB, and Oracle tests",
)
class JsonTableSetReturningFunctionTests(
    SetReturningFunctionOuterJoinMixin,
    TestCase,
):
    table_source_class = JsonTableArrayValue

    @classmethod
    def setUpTestData(cls):
        cls.first = JSONFieldNullable.objects.create(
            json_field=["beta", "alpha", "beta", None]
        )
        cls.second = JSONFieldNullable.objects.create(json_field=["gamma"])
        cls.empty = JSONFieldNullable.objects.create(json_field=[])
        JSONFieldNullable.objects.create(json_field=None)

    def test_json_table_returns_array_elements(self):
        results = (
            JSONFieldNullable.objects.alias(element=JsonTableArrayRow("json_field"))
            .order_by("pk", "element__position")
            .values_list("pk", "element__position", "element__value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN"), 1)
        self.assertIn("JSON_TABLE", sql)
        self.assertNotIn("LATERAL", sql)
        json_null = (
            "" if connection.features.interprets_empty_strings_as_nulls else None
        )
        self.assertSequenceEqual(
            list(results),
            [
                (self.first.pk, 1, "beta"),
                (self.first.pk, 2, "alpha"),
                (self.first.pk, 3, "beta"),
                (self.first.pk, 4, json_null),
                (self.second.pk, 1, "gamma"),
            ],
        )

    def test_json_table_scalar_filter_and_join_reuse(self):
        results = (
            JSONFieldNullable.objects.filter(pk=self.first.pk)
            .alias(element=JsonTableArrayValue("json_field"))
            .filter(element="beta")
            .annotate(value=F("element"))
            .order_by("element")
            .values_list("value", flat=True)
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN"), 1)
        self.assertSequenceEqual(list(results), ["beta", "beta"])

    def test_multiple_json_table_sources(self):
        results = (
            JSONFieldNullable.objects.filter(pk=self.first.pk)
            .alias(
                first=JsonTableArrayValue(Value(["a", "b"], output_field=JSONField())),
                second=JsonTableArrayValue(Value(["x", "y"], output_field=JSONField())),
            )
            .annotate(first_value=F("first"), second_value=F("second"))
            .order_by("first", "second")
            .values_list("first_value", "second_value")
        )
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("CROSS JOIN"), 2)
        self.assertSequenceEqual(
            list(results),
            [
                ("a", "x"),
                ("a", "y"),
                ("b", "x"),
                ("b", "y"),
            ],
        )
