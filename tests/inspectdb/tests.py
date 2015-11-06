# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re
from unittest import skipUnless

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.utils.six import PY3, StringIO

from .models import ColumnTypes


class InspectDBTestCase(TestCase):

    def test_stealth_table_name_filter_option(self):
        out = StringIO()
        # Lets limit the introspection to tables created for models of this
        # application
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_'),
                     stdout=out)
        error_message = "inspectdb has examined a table that should have been filtered out."
        # contrib.contenttypes is one of the apps always installed when running
        # the Django test suite, check that one of its tables hasn't been
        # inspected
        self.assertNotIn("class DjangoContentType(models.Model):", out.getvalue(), msg=error_message)

    def make_field_type_asserter(self):
        """Call inspectdb and return a function to validate a field type in its output"""
        out = StringIO()
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_columntypes'),
                     stdout=out)
        output = out.getvalue()

        def assertFieldType(name, definition):
            out_def = re.search(r'^\s*%s = (models.*)$' % name, output, re.MULTILINE).groups()[0]
            self.assertEqual(definition, out_def)

        return assertFieldType

    def test_field_types(self):
        """Test introspection of various Django field types"""
        assertFieldType = self.make_field_type_asserter()

        # Inspecting Oracle DB doesn't produce correct results (#19884):
        # - it gets max_length wrong: it returns a number of bytes.
        # - it reports fields as blank=True when they aren't.
        if (connection.features.can_introspect_max_length and
                not connection.features.interprets_empty_strings_as_nulls):
            assertFieldType('char_field', "models.CharField(max_length=10)")
            assertFieldType('null_char_field', "models.CharField(max_length=10, blank=True, null=True)")
            assertFieldType('comma_separated_int_field', "models.CharField(max_length=99)")
        assertFieldType('date_field', "models.DateField()")
        assertFieldType('date_time_field', "models.DateTimeField()")
        if (connection.features.can_introspect_max_length and
                not connection.features.interprets_empty_strings_as_nulls):
            assertFieldType('email_field', "models.CharField(max_length=254)")
            assertFieldType('file_field', "models.CharField(max_length=100)")
            assertFieldType('file_path_field', "models.CharField(max_length=100)")
        if connection.features.can_introspect_ip_address_field:
            assertFieldType('ip_address_field', "models.GenericIPAddressField()")
            assertFieldType('gen_ip_adress_field', "models.GenericIPAddressField()")
        elif (connection.features.can_introspect_max_length and
                not connection.features.interprets_empty_strings_as_nulls):
            assertFieldType('ip_address_field', "models.CharField(max_length=15)")
            assertFieldType('gen_ip_adress_field', "models.CharField(max_length=39)")
        if (connection.features.can_introspect_max_length and
                not connection.features.interprets_empty_strings_as_nulls):
            assertFieldType('slug_field', "models.CharField(max_length=50)")
        if not connection.features.interprets_empty_strings_as_nulls:
            assertFieldType('text_field', "models.TextField()")
        if connection.features.can_introspect_time_field:
            assertFieldType('time_field', "models.TimeField()")
        if (connection.features.can_introspect_max_length and
                not connection.features.interprets_empty_strings_as_nulls):
            assertFieldType('url_field', "models.CharField(max_length=200)")

    def test_number_field_types(self):
        """Test introspection of various Django field types"""
        assertFieldType = self.make_field_type_asserter()

        if not connection.features.can_introspect_autofield:
            assertFieldType('id', "models.IntegerField(primary_key=True)  # AutoField?")

        if connection.features.can_introspect_big_integer_field:
            assertFieldType('big_int_field', "models.BigIntegerField()")
        else:
            assertFieldType('big_int_field', "models.IntegerField()")

        bool_field = ColumnTypes._meta.get_field('bool_field')
        bool_field_type = connection.features.introspected_boolean_field_type(bool_field)
        assertFieldType('bool_field', "models.{}()".format(bool_field_type))
        null_bool_field = ColumnTypes._meta.get_field('null_bool_field')
        null_bool_field_type = connection.features.introspected_boolean_field_type(null_bool_field)
        if 'BooleanField' in null_bool_field_type:
            assertFieldType('null_bool_field', "models.{}()".format(null_bool_field_type))
        else:
            if connection.features.can_introspect_null:
                assertFieldType('null_bool_field', "models.{}(blank=True, null=True)".format(null_bool_field_type))
            else:
                assertFieldType('null_bool_field', "models.{}()".format(null_bool_field_type))

        if connection.features.can_introspect_decimal_field:
            assertFieldType('decimal_field', "models.DecimalField(max_digits=6, decimal_places=1)")
        else:       # Guessed arguments on SQLite, see #5014
            assertFieldType('decimal_field', "models.DecimalField(max_digits=10, decimal_places=5)  "
                                             "# max_digits and decimal_places have been guessed, "
                                             "as this database handles decimal fields as float")

        assertFieldType('float_field', "models.FloatField()")

        assertFieldType('int_field', "models.IntegerField()")

        if connection.features.can_introspect_positive_integer_field:
            assertFieldType('pos_int_field', "models.PositiveIntegerField()")
        else:
            assertFieldType('pos_int_field', "models.IntegerField()")

        if connection.features.can_introspect_positive_integer_field:
            if connection.features.can_introspect_small_integer_field:
                assertFieldType('pos_small_int_field', "models.PositiveSmallIntegerField()")
            else:
                assertFieldType('pos_small_int_field', "models.PositiveIntegerField()")
        else:
            if connection.features.can_introspect_small_integer_field:
                assertFieldType('pos_small_int_field', "models.SmallIntegerField()")
            else:
                assertFieldType('pos_small_int_field', "models.IntegerField()")

        if connection.features.can_introspect_small_integer_field:
            assertFieldType('small_int_field', "models.SmallIntegerField()")
        else:
            assertFieldType('small_int_field', "models.IntegerField()")

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_attribute_name_not_python_keyword(self):
        out = StringIO()
        # Lets limit the introspection to tables created for models of this
        # application
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_'),
                     stdout=out)
        output = out.getvalue()
        error_message = "inspectdb generated an attribute name which is a python keyword"
        # Recursive foreign keys should be set to 'self'
        self.assertIn("parent = models.ForeignKey('self')", output)
        self.assertNotIn("from = models.ForeignKey(InspectdbPeople)", output, msg=error_message)
        # As InspectdbPeople model is defined after InspectdbMessage, it should be quoted
        self.assertIn("from_field = models.ForeignKey('InspectdbPeople', db_column='from_id')",
                      output)
        self.assertIn("people_pk = models.ForeignKey(InspectdbPeople, primary_key=True)",
                      output)
        self.assertIn("people_unique = models.ForeignKey(InspectdbPeople, unique=True)",
                      output)

    def test_digits_column_name_introspection(self):
        """Introspection of column names consist/start with digits (#16536/#17676)"""
        out = StringIO()
        # Lets limit the introspection to tables created for models of this
        # application
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_'),
                     stdout=out)
        output = out.getvalue()
        error_message = "inspectdb generated a model field name which is a number"
        self.assertNotIn("    123 = models.CharField", output, msg=error_message)
        self.assertIn("number_123 = models.CharField", output)

        error_message = "inspectdb generated a model field name which starts with a digit"
        self.assertNotIn("    4extra = models.CharField", output, msg=error_message)
        self.assertIn("number_4extra = models.CharField", output)

        self.assertNotIn("    45extra = models.CharField", output, msg=error_message)
        self.assertIn("number_45extra = models.CharField", output)

    def test_special_column_name_introspection(self):
        """
        Introspection of column names containing special characters,
        unsuitable for Python identifiers
        """
        out = StringIO()
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_'),
                     stdout=out)
        output = out.getvalue()
        base_name = 'Field' if not connection.features.uppercases_column_names else 'field'
        self.assertIn("field = models.IntegerField()", output)
        self.assertIn("field_field = models.IntegerField(db_column='%s_')" % base_name, output)
        self.assertIn("field_field_0 = models.IntegerField(db_column='%s__')" % base_name, output)
        self.assertIn("field_field_1 = models.IntegerField(db_column='__field')", output)
        self.assertIn("prc_x = models.IntegerField(db_column='prc(%) x')", output)
        if PY3:
            # Python 3 allows non-ASCII identifiers
            self.assertIn("tamaño = models.IntegerField()", output)
        else:
            self.assertIn("tama_o = models.IntegerField(db_column='tama\\xf1o')", output)

    def test_table_name_introspection(self):
        """
        Introspection of table names containing special characters,
        unsuitable for Python identifiers
        """
        out = StringIO()
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_'),
                     stdout=out)
        output = out.getvalue()
        self.assertIn("class InspectdbSpecialTableName(models.Model):", output)

    def test_managed_models(self):
        """Test that by default the command generates models with `Meta.managed = False` (#14305)"""
        out = StringIO()
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_columntypes'),
                     stdout=out)
        output = out.getvalue()
        self.longMessage = False
        self.assertIn("        managed = False", output, msg='inspectdb should generate unmanaged models.')

    def test_unique_together_meta(self):
        out = StringIO()
        call_command('inspectdb',
                     table_name_filter=lambda tn: tn.startswith('inspectdb_uniquetogether'),
                     stdout=out)
        output = out.getvalue()
        unique_re = re.compile(r'.*unique_together = \((.+),\).*')
        unique_together_match = re.findall(unique_re, output)
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
            call_command('inspectdb',
                         table_name_filter=lambda tn: tn.startswith('inspectdb_columntypes'),
                         stdout=out)
            output = out.getvalue()
            self.assertIn("text_field = myfields.TextField()", output)
            self.assertIn("big_int_field = models.BigIntegerField()", output)
        finally:
            connection.introspection.data_types_reverse = orig_data_types_reverse
