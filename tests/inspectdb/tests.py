# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.utils.unittest import expectedFailure
from django.utils.six import PY3, StringIO

if connection.vendor == 'oracle':
    expectedFailureOnOracle = expectedFailure
else:
    expectedFailureOnOracle = lambda f: f

class InspectDBTestCase(TestCase):

    def test_stealth_table_name_filter_option(self):
        out = StringIO()
        # Lets limit the introspection to tables created for models of this
        # application
        call_command('inspectdb',
                     table_name_filter=lambda tn:tn.startswith('inspectdb_'),
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

    # Inspecting oracle DB doesn't produce correct results, see #19884
    @expectedFailureOnOracle
    def test_field_types(self):
        """Test introspection of various Django field types"""
        assertFieldType = self.make_field_type_asserter()

        assertFieldType('char_field', "models.CharField(max_length=10)")
        assertFieldType('comma_separated_int_field', "models.CharField(max_length=99)")
        assertFieldType('date_field', "models.DateField()")
        assertFieldType('date_time_field', "models.DateTimeField()")
        assertFieldType('email_field', "models.CharField(max_length=75)")
        assertFieldType('file_field', "models.CharField(max_length=100)")
        assertFieldType('file_path_field', "models.CharField(max_length=100)")
        if connection.vendor == 'postgresql':
            # Only PostgreSQL has a specific type
            assertFieldType('ip_address_field', "models.GenericIPAddressField()")
            assertFieldType('gen_ip_adress_field', "models.GenericIPAddressField()")
        else:
            assertFieldType('ip_address_field', "models.CharField(max_length=15)")
            assertFieldType('gen_ip_adress_field', "models.CharField(max_length=39)")
        assertFieldType('slug_field', "models.CharField(max_length=50)")
        assertFieldType('text_field', "models.TextField()")
        assertFieldType('time_field', "models.TimeField()")
        assertFieldType('url_field', "models.CharField(max_length=200)")

    def test_number_field_types(self):
        """Test introspection of various Django field types"""
        assertFieldType = self.make_field_type_asserter()

        assertFieldType('id', "models.IntegerField(primary_key=True)")
        assertFieldType('big_int_field', "models.BigIntegerField()")
        if connection.vendor == 'mysql':
            # No native boolean type on MySQL
            assertFieldType('bool_field', "models.IntegerField()")
            assertFieldType('null_bool_field', "models.IntegerField(blank=True, null=True)")
        else:
            assertFieldType('bool_field', "models.BooleanField()")
            assertFieldType('null_bool_field', "models.NullBooleanField()")
        if connection.vendor == 'sqlite':
            # Guessed arguments, see #5014
            assertFieldType('decimal_field', "models.DecimalField(max_digits=10, decimal_places=5) "
                "# max_digits and decimal_places have been guessed, as this database handles decimal fields as float")
        else:
            assertFieldType('decimal_field', "models.DecimalField(max_digits=6, decimal_places=1)")
        assertFieldType('float_field', "models.FloatField()")
        assertFieldType('int_field', "models.IntegerField()")
        if connection.vendor == 'sqlite':
            assertFieldType('pos_int_field', "models.PositiveIntegerField()")
            assertFieldType('pos_small_int_field', "models.PositiveSmallIntegerField()")
        else:
            # 'unsigned' property undetected on other backends
            assertFieldType('pos_int_field', "models.IntegerField()")
            if connection.vendor == 'postgresql':
                assertFieldType('pos_small_int_field', "models.SmallIntegerField()")
            else:
                assertFieldType('pos_small_int_field', "models.IntegerField()")
        if connection.vendor in ('sqlite', 'postgresql'):
            assertFieldType('small_int_field', "models.SmallIntegerField()")
        else:
            assertFieldType('small_int_field', "models.IntegerField()")

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_attribute_name_not_python_keyword(self):
        out = StringIO()
        # Lets limit the introspection to tables created for models of this
        # application
        call_command('inspectdb',
                     table_name_filter=lambda tn:tn.startswith('inspectdb_'),
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
                     table_name_filter=lambda tn:tn.startswith('inspectdb_'),
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
        call_command('inspectdb', stdout=out)
        output = out.getvalue()
        base_name = 'Field' if connection.vendor != 'oracle' else 'field'
        self.assertIn("field = models.IntegerField()", output)
        self.assertIn("field_field = models.IntegerField(db_column='%s_')" % base_name, output)
        self.assertIn("field_field_0 = models.IntegerField(db_column='%s__')" % base_name, output)
        self.assertIn("field_field_1 = models.IntegerField(db_column='__field')", output)
        self.assertIn("prc_x = models.IntegerField(db_column='prc(%) x')", output)
        if PY3:
            # Python 3 allows non-ascii identifiers
            self.assertIn("tamaño = models.IntegerField()", output)
        else:
            self.assertIn("tama_o = models.IntegerField(db_column='tama\\xf1o')", output)

    def test_managed_models(self):
        """Test that by default the command generates models with `Meta.managed = False` (#14305)"""
        out = StringIO()
        call_command('inspectdb',
                     table_name_filter=lambda tn:tn.startswith('inspectdb_columntypes'),
                     stdout=out)
        output = out.getvalue()
        self.longMessage = False
        self.assertIn("        managed = False", output, msg='inspectdb should generate unmanaged models.')
