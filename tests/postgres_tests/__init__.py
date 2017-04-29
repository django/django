import unittest

from forms_tests.widget_tests.base import WidgetTest

from django.db import connection
from django.db.backends.signals import connection_created
from django.test import TestCase, modify_settings


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class PostgreSQLTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        # No need to keep that signal overhead for non PostgreSQL-related tests.
        from django.contrib.postgres.signals import register_hstore_handler

        connection_created.disconnect(register_hstore_handler)
        super().tearDownClass()


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
# To locate the widget's template.
@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class PostgreSQLWidgetTestCase(WidgetTest):
    pass
