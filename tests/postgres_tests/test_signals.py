from django.db import connection

from . import PostgreSQLTestCase

try:
    from django.contrib.postgres.signals import (
        get_citext_oids,
        get_hstore_oids,
        register_type_handlers,
    )
except ImportError:
    pass  # pyscogp2 isn't installed.


class OIDTests(PostgreSQLTestCase):
    def assertOIDs(self, oids):
        self.assertIsInstance(oids, tuple)
        self.assertGreater(len(oids), 0)
        self.assertTrue(all(isinstance(oid, int) for oid in oids))

    def test_hstore_cache(self):
        get_hstore_oids(connection.alias)
        with self.assertNumQueries(0):
            get_hstore_oids(connection.alias)

    def test_citext_cache(self):
        get_citext_oids(connection.alias)
        with self.assertNumQueries(0):
            get_citext_oids(connection.alias)

    def test_hstore_values(self):
        oids, array_oids = get_hstore_oids(connection.alias)
        self.assertOIDs(oids)
        self.assertOIDs(array_oids)

    def test_citext_values(self):
        oids, citext_oids = get_citext_oids(connection.alias)
        self.assertOIDs(oids)
        self.assertOIDs(citext_oids)

    def test_register_type_handlers_no_db(self):
        """Registering type handlers for the nodb connection does nothing."""
        with connection._nodb_cursor() as cursor:
            register_type_handlers(cursor.db)
