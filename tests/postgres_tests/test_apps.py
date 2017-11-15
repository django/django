from django.db.backends.signals import connection_created
from django.test.utils import modify_settings

from . import PostgreSQLTestCase


class PostgresConfigTests(PostgreSQLTestCase):
    def test_register_type_handlers_connection(self):
        from django.contrib.postgres.signals import register_type_handlers
        self.assertNotIn(register_type_handlers, connection_created._live_receivers(None))
        with modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'}):
            self.assertIn(register_type_handlers, connection_created._live_receivers(None))
        self.assertNotIn(register_type_handlers, connection_created._live_receivers(None))
