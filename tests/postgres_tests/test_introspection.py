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

    def test_postgres_import(self):
        out = StringIO()
        call_command(
            "inspectdb",
            "postgres_tests_hotelreservation",
            "postgres_tests_serialmodel",
            "postgres_tests_room",
            stdout=out,
        )
        output = out.getvalue()
        postgres_import = "from django.contrib import postgres"
        self.assertEqual(output.count(postgres_import), 1, output)
        self.assertLess(output.find(postgres_import), output.find("class "))
        self.assertIn(
            "serial = postgres.fields.SerialField()  "
            "# You may want to consider using AutoField instead.",
            output,
        )
