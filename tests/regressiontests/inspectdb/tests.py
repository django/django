from __future__ import unicode_literals

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.utils.six import StringIO


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
