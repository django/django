import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
class TestsPostGISCreateExtension(TestCase):
    def _extension_exists(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
            return cursor.fetchone()[0] is not None

    def test_extension_is_created(self):
        """Create PostGIS extension if it does not exist."""
        # Make sure extension is not there before we test creation
        with connection.cursor() as cursor:
            cursor.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
        assert not self._extension_exists()

        connection.prepare_database()

        assert self._extension_exists()

    def test_extension_is_not_created(self):
        """Do not attempt to create PostGIS extension if it exists."""

        # TODO: figure out how to test that `CREATE EXTENSION` was not called
        connection.prepare_database()
