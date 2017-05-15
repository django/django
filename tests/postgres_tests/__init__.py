import unittest

from forms_tests.widget_tests.base import WidgetTest

from django.db import connection
from django.db.backends.signals import connection_created
from django.test import TestCase, modify_settings


def skipUnlessPG94(test):
    try:
        PG_VERSION = connection.pg_version
    except AttributeError:
        PG_VERSION = 0
    if PG_VERSION < 90400:
        return unittest.skip('PostgreSQL ≥ 9.4 required')(test)
    return test


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class PostgreSQLTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        # No need to keep that signal overhead for non PostgreSQL-related tests.
        from django.contrib.postgres.signals import register_type_handlers

        connection_created.disconnect(register_type_handlers)
        super().tearDownClass()


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
# To locate the widget's template.
@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class PostgreSQLWidgetTestCase(WidgetTest, PostgreSQLTestCase):
    pass
