import unittest

from django.db import connection
from django.db.models import CompositeField, F, Func, IntegerField, TextField
from django.test import TestCase

from .models import JSONFieldNullable


class JsonEach(Func):
    function = "json_each"
    output_field = TextField(db_column="value")
    set_returning = True


class JsonEachRow(Func):
    function = "json_each"
    output_field = CompositeField(
        key=IntegerField(db_column="key"),
        value=TextField(db_column="value"),
    )
    set_returning = True


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


@unittest.skipUnless(connection.vendor == "sqlite", "SQLite tests")
class SQLiteSetReturningFunctionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.populated = JSONFieldNullable.objects.create(
            json_field=["beta", "alpha", "beta"]
        )
        JSONFieldNullable.objects.create(json_field=[])
        JSONFieldNullable.objects.create(json_field=None)

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
