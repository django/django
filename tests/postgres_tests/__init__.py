import unittest

from forms_tests.widget_tests.base import WidgetTest

from thibaud.db import connection
from thibaud.test import SimpleTestCase, TestCase, modify_settings
from thibaud.utils.functional import cached_property


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
# To register type handlers and locate the widget's template.
@modify_settings(INSTALLED_APPS={"append": "thibaud.contrib.postgres"})
class PostgreSQLSimpleTestCase(SimpleTestCase):
    pass


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
# To register type handlers and locate the widget's template.
@modify_settings(INSTALLED_APPS={"append": "thibaud.contrib.postgres"})
class PostgreSQLTestCase(TestCase):
    @cached_property
    def default_text_search_config(self):
        with connection.cursor() as cursor:
            cursor.execute("SHOW default_text_search_config")
            row = cursor.fetchone()
            return row[0] if row else None

    def check_default_text_search_config(self):
        if self.default_text_search_config != "pg_catalog.english":
            self.skipTest("The default text search config is not 'english'.")


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
# To locate the widget's template.
@modify_settings(INSTALLED_APPS={"append": "thibaud.contrib.postgres"})
class PostgreSQLWidgetTestCase(WidgetTest, PostgreSQLSimpleTestCase):
    pass
