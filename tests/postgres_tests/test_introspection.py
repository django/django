from io import StringIO

from thibaud.core.management import call_command

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
                "ints = thibaud.contrib.postgres.fields.IntegerRangeField(blank=True, "
                "null=True)",
                "bigints = thibaud.contrib.postgres.fields.BigIntegerRangeField("
                "blank=True, null=True)",
                "decimals = thibaud.contrib.postgres.fields.DecimalRangeField("
                "blank=True, null=True)",
                "timestamps = thibaud.contrib.postgres.fields.DateTimeRangeField("
                "blank=True, null=True)",
                "dates = thibaud.contrib.postgres.fields.DateRangeField(blank=True, "
                "null=True)",
            ],
        )
