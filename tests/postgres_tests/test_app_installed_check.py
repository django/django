from django.core import checks
from django.db import models
from django.test import modify_settings
from django.test.utils import isolate_apps

from . import PostgreSQLTestCase
from .fields import (
    ArrayField,
    BigIntegerRangeField,
    DateRangeField,
    DateTimeRangeField,
    DecimalRangeField,
    HStoreField,
    IntegerRangeField,
    SearchVectorField,
)
from .models import PostgreSQLModel

try:
    from django.contrib.postgres.constraints import ExclusionConstraint
    from django.contrib.postgres.fields.ranges import RangeOperators
    from django.contrib.postgres.indexes import GinIndex, PostgresIndex
except ImportError:
    pass


@isolate_apps("postgres_tests")
class TestPostgresAppInstalledCheck(PostgreSQLTestCase):

    def _make_error(self, obj, klass_name):
        """Helper to create postgres.E005 error for specific objects."""
        return checks.Error(
            "'django.contrib.postgres' must be in INSTALLED_APPS in order to "
            f"use {klass_name}.",
            obj=obj,
            id="postgres.E005",
        )

    def assert_model_check_errors(self, model_class, expected_errors):
        errors = model_class.check(databases=self.databases)
        self.assertEqual(errors, [])
        with modify_settings(INSTALLED_APPS={"remove": "django.contrib.postgres"}):
            errors = model_class.check(databases=self.databases)
            self.assertEqual(errors, expected_errors)

    def test_indexes(self):
        class IndexModel(PostgreSQLModel):
            field = models.IntegerField()

            class Meta:
                indexes = [
                    PostgresIndex(fields=["id"], name="postgres_index_test"),
                    GinIndex(fields=["field"], name="gin_index_test"),
                ]

        self.assert_model_check_errors(
            IndexModel,
            [
                self._make_error(IndexModel, "PostgresIndex"),
                self._make_error(IndexModel, "GinIndex"),
            ],
        )

    def test_exclusion_constraint(self):
        class ExclusionModel(PostgreSQLModel):
            value = models.IntegerField()

            class Meta:
                constraints = [
                    ExclusionConstraint(
                        name="exclude_equal",
                        expressions=[("value", RangeOperators.EQUAL)],
                    )
                ]

        self.assert_model_check_errors(
            ExclusionModel, [self._make_error(ExclusionModel, "ExclusionConstraint")]
        )

    def test_array_field(self):
        class ArrayFieldModel(PostgreSQLModel):
            field = ArrayField(models.IntegerField())

        field = ArrayFieldModel._meta.get_field("field")
        self.assert_model_check_errors(
            ArrayFieldModel,
            [self._make_error(field, "ArrayField")],
        )

    def test_nested_array_field(self):
        """Inner ArrayField does not cause a postgres.E001 error."""

        class NestedArrayFieldModel(PostgreSQLModel):
            field = ArrayField(ArrayField(models.IntegerField()))

        field = NestedArrayFieldModel._meta.get_field("field")
        self.assert_model_check_errors(
            NestedArrayFieldModel,
            [
                self._make_error(field, "ArrayField"),
            ],
        )

    def test_hstore_field(self):
        class HStoreFieldModel(PostgreSQLModel):
            field = HStoreField()

        field = HStoreFieldModel._meta.get_field("field")
        self.assert_model_check_errors(
            HStoreFieldModel,
            [
                self._make_error(field, "HStoreField"),
            ],
        )

    def test_range_fields(self):
        class RangeFieldsModel(PostgreSQLModel):
            int_range = IntegerRangeField()
            bigint_range = BigIntegerRangeField()
            decimal_range = DecimalRangeField()
            datetime_range = DateTimeRangeField()
            date_range = DateRangeField()

        expected_errors = [
            self._make_error(field, field.__class__.__name__)
            for field in [
                RangeFieldsModel._meta.get_field("int_range"),
                RangeFieldsModel._meta.get_field("bigint_range"),
                RangeFieldsModel._meta.get_field("decimal_range"),
                RangeFieldsModel._meta.get_field("datetime_range"),
                RangeFieldsModel._meta.get_field("date_range"),
            ]
        ]
        self.assert_model_check_errors(RangeFieldsModel, expected_errors)

    def test_search_vector_field(self):
        class SearchModel(PostgreSQLModel):
            search_field = SearchVectorField()

        field = SearchModel._meta.get_field("search_field")
        self.assert_model_check_errors(
            SearchModel,
            [
                self._make_error(field, "SearchVectorField"),
            ],
        )
