from StringIO import StringIO

from django.core.management import call_command
from django.test import TestCase


class InspectDBTestCase(TestCase):
    def test_attribute_name_not_python_keyword(self):
        out = StringIO()
        call_command('inspectdb', stdout=out)
        error_message = "inspectdb generated an attribute name which is a python keyword"
        self.assertFalse("from = models.ForeignKey(InspectdbPeople)" in out.getvalue(), msg=error_message)
        self.assertTrue("from_field = models.ForeignKey(InspectdbPeople)" in out.getvalue())
        out.close()
