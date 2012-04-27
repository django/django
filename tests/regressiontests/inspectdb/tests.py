from StringIO import StringIO

from django.core.management import call_command
from django.test import TestCase, skipUnlessDBFeature


class InspectDBTestCase(TestCase):

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_attribute_name_not_python_keyword(self):
        out = StringIO()
        call_command('inspectdb', stdout=out)
        error_message = "inspectdb generated an attribute name which is a python keyword"
        self.assertNotIn("from = models.ForeignKey(InspectdbPeople)", out.getvalue(), msg=error_message)
        # As InspectdbPeople model is defined after InspectdbMessage, it should be quoted
        self.assertIn("from_field = models.ForeignKey('InspectdbPeople')", out.getvalue())
        self.assertIn("people_pk = models.ForeignKey(InspectdbPeople, primary_key=True)",
            out.getvalue())
        self.assertIn("people_unique = models.ForeignKey(InspectdbPeople, unique=True)",
            out.getvalue())
        out.close()

    def test_digits_column_name_introspection(self):
        """Introspection of column names consist/start with digits (#16536/#17676)"""
        out = StringIO()
        call_command('inspectdb', stdout=out)
        error_message = "inspectdb generated a model field name which is a number"
        self.assertNotIn("    123 = models.CharField", out.getvalue(), msg=error_message)
        self.assertIn("number_123 = models.CharField", out.getvalue())

        error_message = "inspectdb generated a model field name which starts with a digit"
        self.assertNotIn("    4extra = models.CharField", out.getvalue(), msg=error_message)
        self.assertIn("number_4extra = models.CharField", out.getvalue())

        self.assertNotIn("    45extra = models.CharField", out.getvalue(), msg=error_message)
        self.assertIn("number_45extra = models.CharField", out.getvalue())
