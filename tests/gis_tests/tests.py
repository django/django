import unittest

from django.core.exceptions import ImproperlyConfigured
from django.db import ProgrammingError, connection
from django.db.backends.base.base import NO_DB_ALIAS
from django.test import TestCase

try:
    from django.contrib.gis.db.backends.postgis.operations import PostGISOperations

    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False


class BaseSpatialFeaturesTests(TestCase):
    def test_invalid_has_func_function(self):
        msg = (
            'DatabaseFeatures.has_Invalid_function isn\'t valid. Is "Invalid" '
            "missing from BaseSpatialOperations.unsupported_functions?"
        )
        with self.assertRaisesMessage(ValueError, msg):
            connection.features.has_Invalid_function


if HAS_POSTGRES:

    class FakeConnection:
        def __init__(self):
            self.settings_dict = {
                "NAME": "test",
            }

    class FakePostGISOperations(PostGISOperations):
        def __init__(self, version=None):
            self.version = version
            self.connection = FakeConnection()

        def _get_postgis_func(self, func):
            if func == "postgis_lib_version":
                if self.version is None:
                    raise ProgrammingError
                else:
                    return self.version
            elif func == "version":
                pass
            else:
                raise NotImplementedError("This function was not expected to be called")


@unittest.skipUnless(HAS_POSTGRES, "The psycopg driver is needed for these tests")
class TestPostGISVersionCheck(unittest.TestCase):
    """
    The PostGIS version check parses correctly the version numbers
    """

    def test_get_version(self):
        expect = "1.0.0"
        ops = FakePostGISOperations(expect)
        actual = ops.postgis_lib_version()
        self.assertEqual(expect, actual)

    def test_version_classic_tuple(self):
        expect = ("1.2.3", 1, 2, 3)
        ops = FakePostGISOperations(expect[0])
        actual = ops.postgis_version_tuple()
        self.assertEqual(expect, actual)

    def test_version_dev_tuple(self):
        expect = ("1.2.3dev", 1, 2, 3)
        ops = FakePostGISOperations(expect[0])
        actual = ops.postgis_version_tuple()
        self.assertEqual(expect, actual)

    def test_version_loose_tuple(self):
        expect = ("1.2.3b1.dev0", 1, 2, 3)
        ops = FakePostGISOperations(expect[0])
        actual = ops.postgis_version_tuple()
        self.assertEqual(expect, actual)

    def test_valid_version_numbers(self):
        versions = [
            ("1.3.0", 1, 3, 0),
            ("2.1.1", 2, 1, 1),
            ("2.2.0dev", 2, 2, 0),
        ]

        for version in versions:
            with self.subTest(version=version):
                ops = FakePostGISOperations(version[0])
                actual = ops.spatial_version
                self.assertEqual(version[1:], actual)

    def test_no_version_number(self):
        ops = FakePostGISOperations()
        with self.assertRaises(ImproperlyConfigured):
            ops.spatial_version


@unittest.skipUnless(HAS_POSTGRES, "PostGIS-specific tests.")
class TestPostGISBackend(unittest.TestCase):
    def test_non_db_connection_classes(self):
        from django.contrib.gis.db.backends.postgis.base import DatabaseWrapper
        from django.db.backends.postgresql.features import DatabaseFeatures
        from django.db.backends.postgresql.introspection import DatabaseIntrospection
        from django.db.backends.postgresql.operations import DatabaseOperations

        wrapper = DatabaseWrapper(settings_dict={}, alias=NO_DB_ALIAS)
        # PostGIS-specific stuff is not initialized for non-db connections.
        self.assertIs(wrapper.features_class, DatabaseFeatures)
        self.assertIs(wrapper.ops_class, DatabaseOperations)
        self.assertIs(wrapper.introspection_class, DatabaseIntrospection)
