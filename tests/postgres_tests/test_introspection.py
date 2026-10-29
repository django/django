from io import StringIO

from django.core.management import call_command

from . import PostgreSQLTestCase


class InspectDBTests(PostgreSQLTestCase):
    def assertFieldsInModel(self, model, field_outputs):
        out = StringIO()
        call_command(
            "inspectdb",
            table_name_filter=lambda tn: tn.startswith(model),
            stdout=out,
        )
        output = out.getvalue()
        for field_output in field_outputs:
            self.assertIn(field_output, output)

    def test_range_fields(self):
        self.assertFieldsInModel(
            "postgres_tests_rangesmodel",
            [
                "ints = django.contrib.postgres.fields.IntegerRangeField(blank=True, "
                "null=True)",
                "bigints = django.contrib.postgres.fields.BigIntegerRangeField("
                "blank=True, null=True)",
                "decimals = django.contrib.postgres.fields.DecimalRangeField("
                "blank=True, null=True)",
                "timestamps = django.contrib.postgres.fields.DateTimeRangeField("
                "blank=True, null=True)",
                "dates = django.contrib.postgres.fields.DateRangeField(blank=True, "
                "null=True)",
            ],
        )

    def test_hstore_field(self):
        from django.db.backends.postgresql.base import psycopg_version

        if psycopg_version() < (3, 2):
            self.skipTest("psycopg 3.2+ is required.")
        self.assertFieldsInModel(
            "postgres_tests_hstoremodel",
            [
                "field = django.contrib.postgres.fields.HStoreField(blank=True, "
                "null=True)",
            ],
        )
