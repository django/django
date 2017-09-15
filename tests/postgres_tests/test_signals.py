from django.db import connection

from . import PostgreSQLTestCase

try:
    from django.contrib.postgres.signals import get_hstore_oids, get_citext_oids
except ImportError:
    pass  # pyscogp2 isn't installed.


class OIDTests(PostgreSQLTestCase):

    def assertOIDs(self, oids):
        self.assertIsInstance(oids, tuple)
        self.assertGreater(len(oids), 0)
        self.assertTrue(all(isinstance(oid, int) for oid in oids))

    def test_hstore_cache(self):
        with self.assertNumQueries(0):
            get_hstore_oids(connection.alias)

    def test_citext_cache(self):
        with self.assertNumQueries(0):
            get_citext_oids(connection.alias)

    def test_hstore_values(self):
        oids, array_oids = get_hstore_oids(connection.alias)
        self.assertOIDs(oids)
        self.assertOIDs(array_oids)

    def test_citext_values(self):
        oids = get_citext_oids(connection.alias)
        self.assertOIDs(oids)
