from io import StringIO

from django.core.management import call_command
from django.test.utils import modify_settings

from . import PostgreSQLTestCase


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class InspectDBTests(PostgreSQLTestCase):
    def assertFieldsInModel(self, model, field_outputs):
        out = StringIO()
        call_command(
            'inspectdb',
            table_name_filter=lambda tn: tn.startswith(model),
            stdout=out,
        )
        output = out.getvalue()
        for field_output in field_outputs:
            self.assertIn(field_output, output)

    def test_json_field(self):
        self.assertFieldsInModel(
            'postgres_tests_jsonmodel',
            ['field = django.contrib.postgresql.fields.JSONField(blank=True, null=True)'],
        )

    def test_hstore_introspection(self):
        self.assertFieldsInModel(
            'postgres_tests_hstoremodel',
            ['field = django.contrib.postgresql.fields.HStoreField(blank=True, null=True)'],
        )

    def test_array_introspection(self):
        """
        Note that nested arrays do not seem to be introspectable.
        """
        self.assertFieldsInModel(
            'postgres_tests_integerarraymodel',
            ['field = django.contrib.postgresql.fields.ArrayField(models.IntegerField())'],
        )
        self.assertFieldsInModel(
            'postgres_tests_nullableintegerarraymodel',
            ['field = django.contrib.postgresql.fields.ArrayField(models.IntegerField(), blank=True, null=True)'],
        )
        self.assertFieldsInModel(
            'postgres_tests_chararraymodel',
            ['field = django.contrib.postgresql.fields.ArrayField(models.CharField(max_length=10))'],
        )
        self.assertFieldsInModel(
            'postgres_tests_datetimearraymodel',
            [
                'datetimes = django.contrib.postgresql.fields.ArrayField(models.DateTimeField())',
                'dates = django.contrib.postgresql.fields.ArrayField(models.DateField())',
                'times = django.contrib.postgresql.fields.ArrayField(models.TimeField())',
            ],
        )
        self.assertFieldsInModel(
            'postgres_tests_othertypesarraymodel',
            [
                'bools = django.contrib.postgresql.fields.ArrayField(models.BooleanField())',
                'texts = django.contrib.postgresql.fields.ArrayField(models.TextField())',
                'ips = django.contrib.postgresql.fields.ArrayField(models.GenericIPAddressField())',
                'uuids = django.contrib.postgresql.fields.ArrayField(models.UUIDField())',
                'decimals = django.contrib.postgresql.fields.ArrayField'
                '(models.DecimalField(max_digits=5, decimal_places=2))',
                'tags = django.contrib.postgresql.fields.ArrayField'
                '(models.SmallIntegerField(), blank=True, null=True)',
            ],
        )

    def test_range_fields(self):
        self.assertFieldsInModel(
            'postgres_tests_rangesmodel',
            [
                'ints = django.contrib.postgresql.fields.IntegerRangeField(blank=True, null=True)',
                'bigints = django.contrib.postgresql.fields.BigIntegerRangeField(blank=True, null=True)',
                'floats = django.contrib.postgresql.fields.FloatRangeField(blank=True, null=True)',
                'timestamps = django.contrib.postgresql.fields.DateTimeRangeField(blank=True, null=True)',
                'dates = django.contrib.postgresql.fields.DateRangeField(blank=True, null=True)',
            ],
        )
