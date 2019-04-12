import unittest

from forms_tests.widget_tests.base import WidgetTest

from django.db import connection
from django.test import SimpleTestCase, TestCase, modify_settings


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
class PostgreSQLSimpleTestCase(SimpleTestCase):
    pass


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
class PostgreSQLTestCase(TestCase):
    pass


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
# To locate the widget's template.
@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
class PostgreSQLWidgetTestCase(WidgetTest, PostgreSQLSimpleTestCase):
    pass
