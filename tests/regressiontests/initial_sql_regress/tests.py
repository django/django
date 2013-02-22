import os
import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.color import no_style
from django.core.management.sql import custom_sql_for_model
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models.loading import cache, load_app
from django.test import TestCase
from django.test.utils import override_settings

from .models import Simple


class InitialSQLTests(TestCase):
    # The format of the included SQL file for this test suite is important.
    # It must end with a trailing newline in order to test the fix for #2161.

    def test_initial_sql(self):
        # As pointed out by #14661, test data loaded by custom SQL
        # can't be relied upon; as a result, the test framework flushes the
        # data contents before every test. This test validates that this has
        # occurred.
        self.assertEqual(Simple.objects.count(), 0)

    def test_custom_sql(self):
        # Simulate the custom SQL loading by syncdb
        connection = connections[DEFAULT_DB_ALIAS]
        custom_sql = custom_sql_for_model(Simple, no_style(), connection)
        self.assertEqual(len(custom_sql), 8)
        cursor = connection.cursor()
        for sql in custom_sql:
            cursor.execute(sql)
        self.assertEqual(Simple.objects.count(), 8)


@override_settings(INSTALLED_APPS=('app3', ))
class InitialSQLLocationTests(TestCase):
    """
    This test is based on `ProxyModelInheritanceTests` although it checks something different.
    """
    def setUp(self):
        self.old_sys_path = sys.path[:]
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        for app in settings.INSTALLED_APPS:
            load_app(app)

    def tearDown(self):
        sys.path = self.old_sys_path
        del cache.app_store[cache.app_labels['app3']]
        del cache.app_labels['app3']
        del cache.app_models['app3']
        del cache.handled['app3']

    def test_load_custom_sql(self):
        # Test locations of custom SQL
        from .app3.models import Simple2
        call_command('syncdb', verbosity=0)
        self.assertTrue(Simple2.objects.filter(name='James').count(), 1)
        self.assertTrue(Simple2.objects.filter(name='John').count(), 1)
