import os
import re
from io import StringIO
from unittest import mock, skipUnless

from django.core.management import call_command
from django.db import connection
from django.db.backends.base.introspection import TableInfo
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from .models import PeopleMoreData, test_collation


def inspectdb_tables_only(table_name):
    """
    Limit introspection to tables created for models of this app.
    Some databases such as Oracle are extremely slow at introspection.
    """
    return table_name.startswith('inspectdb_')


def inspectdb_views_only(table_name):
    return (
        table_name.startswith('inspectdb_') and
        table_name.endswith(('_materialized', '_view'))
    )


def special_table_only(table_name):
    return table_name.startswith('inspectdb_special')


class InspectDBTestCase(TestCase):
    unique_re = re.compile(r'.*unique_together = \((.+),\).*')

    def test_stealth_table_name_filter_option(self):
        out = StringIO()
        call_command('inspectdb', table_name_filter=inspectdb_tables_only, stdout=out)
        error_message = "inspectdb has examined a table that should have been filtered out."
        # contrib.contenttypes is one of the apps always installed when running
        # the Django test suite, check that one of its tables hasn't been
        # inspected
        self.assertNotIn("class DjangoContentType(models.Model):", out.getvalue(), msg=error_message)

    def test_table_option(self):
        """
        inspectdb can inspect a subset of tables by passing the table names as
        arguments.
        """
        out = StringIO()
        call_command('inspectdb', 'inspectdb_people', stdout=out)
        output = out.getvalue()
        self.assertIn('class InspectdbPeople(models.Model):', output)
        self.assertNotIn("InspectdbPeopledata", output)

    def make_field_type_asserter(self):
        """Call inspectdb and return a function to validate a field type in its output"""
        out = StringIO()
        call_command('inspectdb', 'inspectdb_columntypes', stdout=out)
        output = out.getvalue()

        def assertFieldType(name, definition):
            out_def = re.search(r'^\s*%s = (models.*)$' % name, output, re.MULTILINE)[1]
            self.assertEqual(definition, out_def)

        return assertFieldType

    def test_field_types(self):
        """Test introspection of various Django field types"""
        assertFieldType = self.make_field_type_asserter()
        introspected_field_types = connection.features.introspected_field_types
        char_field_type = introspected_field_types['CharField']
        # Inspecting Oracle DB doesn't produce correct results (#19884):
        # - it reports fields as blank=True when they aren't.
        if not connection.features.interprets_empty_strings_as_nulls and char_field_type == 'CharField':
            assertFieldType('char_field', "models.CharField(max_length=10)")
            assertFieldType('null_char_field', "models.CharField(max_length=10, blank=True, null=True)")
            assertFieldType('email_field', "models.CharField(max_length=254)")
            assertFieldType('file_field', "models.CharField(max_length=100)")
            assertFieldType('file_path_field', "models.CharField(max_length=100)")
            assertFieldType('slug_field', "models.CharField(max_length=50)")
            assertFieldType('text_field', "models.TextField()")
            assertFieldType('url_field', "models.CharField(max_length=200)")
        if char_field_type == 'TextField':
            assertFieldType('char_field', 'models.TextField()')
            assertFieldType('null_char_field', 'models.TextField(blank=True, null=True)')
            assertFieldType('email_field', 'models.TextField()')
            assertFieldType('file_field', 'models.TextField()')
            assertFieldType('file_path_field', 'models.TextField()')
            assertFieldType('slug_field', 'models.TextField()')
            assertFieldType('text_field', 'models.TextField()')
            assertFieldType('url_field', 'models.TextField()')
        assertFieldType('date_field', "models.DateField()")
        assertFieldType('date_time_field', "models.DateTimeField()")
        if introspected_field_types['GenericIPAddressField'] == 'GenericIPAddressField':
            assertFieldType('gen_ip_address_field', "models.GenericIPAddressField()")
        elif not connection.features.interprets_empty_strings_as_nulls:
            assertFieldType('gen_ip_address_field', "models.CharField(max_length=39)")
        assertFieldType('time_field', 'models.%s()' % introspected_field_types['TimeField'])
        if connection.features.has_native_uuid_field:
            assertFieldType('uuid_field', "models.UUIDField()")
        elif not connection.features.interprets_empty_strings_as_nulls:
            assertFieldType('uuid_field', "models.CharField(max_length=32)")

    @skipUnlessDBFeature('can_introspect_json_field', 'supports_json_field')
    def test_json_field(self):
        out = StringIO()
        call_command('inspectdb', 'inspectdb_jsonfieldcolumntype', stdout=out)
        output = out.getvalue()
        if not connection.features.interprets_empty_strings_as_nulls:
            self.assertIn('json_field = models.JSONField()', output)
        self.assertIn('null_json_field = models.JSONField(blank=True, null=True)', output)

    @skipUnlessDBFeature('supports_collation_on_charfield')
    @skipUnless(test_collation, 'Language collations are not supported.')
    def test_char_field_db_collation(self):
        out = StringIO()
        call_command('inspectdb', 'inspectdb_charfielddbcollation', stdout=out)
        output = out.getvalue()
        if not connection.features.interprets_empty_strings_as_nulls:
            self.assertIn(
                "char_field = models.CharField(max_length=10, "
                "db_collation='%s')" % test_collation,
                output,
            )
        else:
            self.assertIn(
                "char_field = models.CharField(max_length=10, "
                "db_collation='%s', blank=True, null=True)" % test_collation,
                output,
            )

    @skipUnlessDBFeature('supports_collation_on_textfield')
    @skipUnless(test_collation, 'Language collations are not supported.')
    def test_text_field_db_collation(self):
        out = StringIO()
        call_command('inspectdb', 'inspectdb_textfielddbcollation', stdout=out)
        output = out.getvalue()
        if not connection.features.interprets_empty_strings_as_nulls:
            self.assertIn(
                "text_field = models.TextField(db_collation='%s')" % test_collation,
                output,
            )
        else:
            self.assertIn(
                "text_field = models.TextField(db_collation='%s, blank=True, "
                "null=True)" % test_collation,
                output,
            )

    def test_number_field_types(self):
        """Test introspection of various Django field types"""
        assertFieldType = self.make_field_type_asserter()
        introspected_field_types = connection.features.introspected_field_types

        auto_field_type = connection.features.introspected_field_types['AutoField']
        if auto_field_type != 'AutoField':
            assertFieldType('id', "models.%s(primary_key=True)  # AutoField?" % auto_field_type)

        assertFieldType('big_int_field', 'models.%s()' % introspected_field_types['BigIntegerField'])

        bool_field_type = introspected_field_types['BooleanField']
        assertFieldType('bool_field', "models.{}()".format(bool_field_type))
        assertFieldType('null_bool_field', 'models.{}(blank=True, null=True)'.format(bool_field_type))

        if connection.vendor != 'sqlite':
            assertFieldType('decimal_field', "models.DecimalField(max_digits=6, decimal_places=1)")
        else:       # Guessed arguments on SQLite, see #5014
            assertFieldType('decimal_field', "models.DecimalField(max_digits=10, decimal_places=5)  "
                                             "# max_digits and decimal_places have been guessed, "
                                             "as this database handles decimal fields as float")

        assertFieldType('float_field', "models.FloatField()")
        assertFieldType('int_field', 'models.%s()' % introspected_field_types['IntegerField'])
        assertFieldType('pos_int_field', 'models.%s()' % introspected_field_types['PositiveIntegerField'])
        assertFieldType('pos_big_int_field', 'models.%s()' % introspected_field_types['PositiveBigIntegerField'])
        assertFieldType('pos_small_int_field', 'models.%s()' % introspected_field_types['PositiveSmallIntegerField'])
        assertFieldType('small_int_field', 'models.%s()' % introspected_field_types['SmallIntegerField'])

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_attribute_name_not_python_keyword(self):
        out = StringIO()
        call_command('inspectdb', table_name_filter=inspectdb_tables_only, stdout=out)
        output = out.getvalue()
        error_message = "inspectdb generated an attribute name which is a Python keyword"
        # Recursive foreign keys should be set to 'self'
        self.assertIn("parent = models.ForeignKey('self', models.DO_NOTHING)", output)
        self.assertNotIn(
            "from = models.ForeignKey(InspectdbPeople, models.DO_NOTHING)",
            output,
            msg=error_message,
        )
        # As InspectdbPeople model is defined after InspectdbMessage, it should be quoted
        self.assertIn(
            "from_field = models.ForeignKey('InspectdbPeople', models.DO_NOTHING, db_column='from_id')",
            output,
        )
        self.assertIn(
            'people_pk = models.OneToOneField(InspectdbPeople, models.DO_NOTHING, primary_key=True)',
            output,
        )
        self.assertIn(
            'people_unique = models.OneToOneField(InspectdbPeople, models.DO_NOTHING)',
            output,
        )

    def test_digits_column_name_introspection(self):
        """Introspection of column names consist/start with digits (#16536/#17676)"""
        char_field_type = connection.features.introspected_field_types['CharField']
        out = StringIO()
        call_command('inspectdb', 'inspectdb_digitsincolumnname', stdout=out)
        output = out.getvalue()
        error_message = "inspectdb generated a model field name which is a number"
        self.assertNotIn('    123 = models.%s' % char_field_type, output, msg=error_message)
        self.assertIn('number_123 = models.%s' % char_field_type, output)

        error_message = "inspectdb generated a model field name which starts with a digit"
        self.assertNotIn('    4extra = models.%s' % char_field_type, output, msg=error_message)
        self.assertIn('number_4extra = models.%s' % char_field_type, output)

        self.assertNotIn('    45extra = models.%s' % char_field_type, output, msg=error_message)
        self.assertIn('number_45extra = models.%s' % char_field_type, output)

    def test_special_column_name_introspection(self):
        """
        Introspection of column names containing special characters,
        unsuitable for Python identifiers
        """
        out = StringIO()
        call_command('inspectdb', table_name_filter=special_table_only, stdout=out)
        output = out.getvalue()
        base_name = connection.introspection.identifier_converter('Field')
        integer_field_type = connection.features.introspected_field_types['IntegerField']
        self.assertIn("field = models.%s()" % integer_field_type, output)
        self.assertIn("field_field = models.%s(db_column='%s_')" % (integer_field_type, base_name), output)
        self.assertIn("field_field_0 = models.%s(db_column='%s__')" % (integer_field_type, base_name), output)
        self.assertIn("field_field_1 = models.%s(db_column='__field')" % integer_field_type, output)
        self.assertIn("prc_x = models.{}(db_column='prc(%) x')".format(integer_field_type), output)
        self.assertIn("tamaño = models.%s()" % integer_field_type, output)

    def test_table_name_introspection(self):
        """
        Introspection of table names containing special characters,
        unsuitable for Python identifiers
        """
        out = StringIO()
        call_command('inspectdb', table_name_filter=special_table_only, stdout=out)
        output = out.getvalue()
        self.assertIn("class InspectdbSpecialTableName(models.Model):", output)

    def test_managed_models(self):
        """By default the command generates models with `Meta.managed = False` (#14305)"""
        out = StringIO()
        call_command('inspectdb', 'inspectdb_columntypes', stdout=out)
        output = out.getvalue()
        self.longMessage = False
        self.assertIn("        managed = False", output, msg='inspectdb should generate unmanaged models.')

    def test_unique_together_meta(self):
        out = StringIO()
        call_command('inspectdb', 'inspectdb_uniquetogether', stdout=out)
        output = out.getvalue()
        self.assertIn("    unique_together = (('", output)
        unique_together_match = self.unique_re.findall(output)
        # There should be one unique_together tuple.
        self.assertEqual(len(unique_together_match), 1)
        fields = unique_together_match[0]
        # Fields with db_column = field name.
        self.assertIn("('field1', 'field2')", fields)
        # Fields from columns whose names are Python keywords.
        self.assertIn("('field1', 'field2')", fields)
        # Fields whose names normalize to the same Python field name and hence
        # are given an integer suffix.
        self.assertIn("('non_unique_column', 'non_unique_column_0')", fields)

    @skipUnless(connection.vendor == 'postgresql', 'PostgreSQL specific SQL')
    def test_unsupported_unique_together(self):
        """Unsupported index types (COALESCE here) are skipped."""
        with connection.cursor() as c:
            c.execute(
                'CREATE UNIQUE INDEX Findex ON %s '
                '(id, people_unique_id, COALESCE(message_id, -1))' % PeopleMoreData._meta.db_table
            )
        try:
            out = StringIO()
            call_command(
                'inspectdb',
                table_name_filter=lambda tn: tn.startswith(PeopleMoreData._meta.db_table),
                stdout=out,
            )
            output = out.getvalue()
            self.assertIn('# A unique constraint could not be introspected.', output)
            self.assertEqual(self.unique_re.findall(output), ["('id', 'people_unique')"])
        finally:
            with connection.cursor() as c:
                c.execute('DROP INDEX Findex')

    @skipUnless(connection.vendor == 'sqlite',
                "Only patched sqlite's DatabaseIntrospection.data_types_reverse for this test")
    def test_custom_fields(self):
        """
        Introspection of columns with a custom field (#21090)
        """
        out = StringIO()
        orig_data_types_reverse = connection.introspection.data_types_reverse
        try:
            connection.introspection.data_types_reverse = {
                'text': 'myfields.TextField',
                'bigint': 'BigIntegerField',
            }
            call_command('inspectdb', 'inspectdb_columntypes', stdout=out)
            output = out.getvalue()
            self.assertIn("text_field = myfields.TextField()", output)
            self.assertIn("big_int_field = models.BigIntegerField()", output)
        finally:
            connection.introspection.data_types_reverse = orig_data_types_reverse

    def test_introspection_errors(self):
        """
        Introspection errors should not crash the command, and the error should
        be visible in the output.
        """
        out = StringIO()
        with mock.patch('django.db.connection.introspection.get_table_list',
                        return_value=[TableInfo(name='nonexistent', type='t')]):
            call_command('inspectdb', stdout=out)
        output = out.getvalue()
        self.assertIn("# Unable to inspect table 'nonexistent'", output)
        # The error message depends on the backend
        self.assertIn("# The error was:", output)


class InspectDBTransactionalTests(TransactionTestCase):
    available_apps = ['inspectdb']

    def test_include_views(self):
        """inspectdb --include-views creates models for database views."""
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE VIEW inspectdb_people_view AS '
                'SELECT id, name FROM inspectdb_people'
            )
        out = StringIO()
        view_model = 'class InspectdbPeopleView(models.Model):'
        view_managed = 'managed = False  # Created from a view.'
        try:
            call_command(
                'inspectdb',
                table_name_filter=inspectdb_views_only,
                stdout=out,
            )
            no_views_output = out.getvalue()
            self.assertNotIn(view_model, no_views_output)
            self.assertNotIn(view_managed, no_views_output)
            call_command(
                'inspectdb',
                table_name_filter=inspectdb_views_only,
                include_views=True,
                stdout=out,
            )
            with_views_output = out.getvalue()
            self.assertIn(view_model, with_views_output)
            self.assertIn(view_managed, with_views_output)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP VIEW inspectdb_people_view')

    @skipUnlessDBFeature('can_introspect_materialized_views')
    def test_include_materialized_views(self):
        """inspectdb --include-views creates models for materialized views."""
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE MATERIALIZED VIEW inspectdb_people_materialized AS '
                'SELECT id, name FROM inspectdb_people'
            )
        out = StringIO()
        view_model = 'class InspectdbPeopleMaterialized(models.Model):'
        view_managed = 'managed = False  # Created from a view.'
        try:
            call_command(
                'inspectdb',
                table_name_filter=inspectdb_views_only,
                stdout=out,
            )
            no_views_output = out.getvalue()
            self.assertNotIn(view_model, no_views_output)
            self.assertNotIn(view_managed, no_views_output)
            call_command(
                'inspectdb',
                table_name_filter=inspectdb_views_only,
                include_views=True,
                stdout=out,
            )
            with_views_output = out.getvalue()
            self.assertIn(view_model, with_views_output)
            self.assertIn(view_managed, with_views_output)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP MATERIALIZED VIEW inspectdb_people_materialized')

    @skipUnless(connection.vendor == 'postgresql', 'PostgreSQL specific SQL')
    @skipUnlessDBFeature('supports_table_partitions')
    def test_include_partitions(self):
        """inspectdb --include-partitions creates models for partitions."""
        with connection.cursor() as cursor:
            cursor.execute('''\
                CREATE TABLE inspectdb_partition_parent (name text not null)
                PARTITION BY LIST (left(upper(name), 1))
            ''')
            cursor.execute('''\
                CREATE TABLE inspectdb_partition_child
                PARTITION OF inspectdb_partition_parent
                FOR VALUES IN ('A', 'B', 'C')
            ''')
        out = StringIO()
        partition_model_parent = 'class InspectdbPartitionParent(models.Model):'
        partition_model_child = 'class InspectdbPartitionChild(models.Model):'
        partition_managed = 'managed = False  # Created from a partition.'
        try:
            call_command('inspectdb', table_name_filter=inspectdb_tables_only, stdout=out)
            no_partitions_output = out.getvalue()
            self.assertIn(partition_model_parent, no_partitions_output)
            self.assertNotIn(partition_model_child, no_partitions_output)
            self.assertNotIn(partition_managed, no_partitions_output)
            call_command('inspectdb', table_name_filter=inspectdb_tables_only, include_partitions=True, stdout=out)
            with_partitions_output = out.getvalue()
            self.assertIn(partition_model_parent, with_partitions_output)
            self.assertIn(partition_model_child, with_partitions_output)
            self.assertIn(partition_managed, with_partitions_output)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP TABLE IF EXISTS inspectdb_partition_child')
                cursor.execute('DROP TABLE IF EXISTS inspectdb_partition_parent')

    @skipUnless(connection.vendor == 'postgresql', 'PostgreSQL specific SQL')
    def test_foreign_data_wrapper(self):
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS file_fdw')
            cursor.execute('CREATE SERVER inspectdb_server FOREIGN DATA WRAPPER file_fdw')
            cursor.execute('''\
                CREATE FOREIGN TABLE inspectdb_iris_foreign_table (
                    petal_length real,
                    petal_width real,
                    sepal_length real,
                    sepal_width real
                ) SERVER inspectdb_server OPTIONS (
                    filename %s
                )
            ''', [os.devnull])
        out = StringIO()
        foreign_table_model = 'class InspectdbIrisForeignTable(models.Model):'
        foreign_table_managed = 'managed = False'
        try:
            call_command(
                'inspectdb',
                table_name_filter=inspectdb_tables_only,
                stdout=out,
            )
            output = out.getvalue()
            self.assertIn(foreign_table_model, output)
            self.assertIn(foreign_table_managed, output)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP FOREIGN TABLE IF EXISTS inspectdb_iris_foreign_table')
                cursor.execute('DROP SERVER IF EXISTS inspectdb_server')
                cursor.execute('DROP EXTENSION IF EXISTS file_fdw')
