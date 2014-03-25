import unittest

from django.contrib.gis.db.backends.postgis.operations import PostGISOperations
from django.core.exceptions import ImproperlyConfigured
from django.db import ProgrammingError


class FakeConnection(object):
    def __init__(self):
        self.settings_dict = {
            'NAME': 'test',
        }


class FakePostGISOperations(PostGISOperations):
    def __init__(self, version=None):
        self.version = version
        self.connection = FakeConnection()

    def _get_postgis_func(self, func):
        if func == 'postgis_lib_version':
            if self.version is None:
                raise ProgrammingError
            else:
                return self.version
        else:
            raise NotImplementedError('This function was not expected to be called')


class TestPostgisVersionCheck(unittest.TestCase):
    """
    Tests that the postgis version check parses correctly the version numbers
    """

    def test_get_version(self):
        expect = '1.0.0'
        ops = FakePostGISOperations(expect)
        actual = ops.postgis_lib_version()
        self.assertEqual(expect, actual)

    def test_version_classic_tuple(self):
        expect = ('1.2.3', 1, 2, 3)
        ops = FakePostGISOperations(expect[0])
        actual = ops.postgis_version_tuple()
        self.assertEqual(expect, actual)

    def test_version_dev_tuple(self):
        expect = ('1.2.3dev', 1, 2, 3)
        ops = FakePostGISOperations(expect[0])
        actual = ops.postgis_version_tuple()
        self.assertEqual(expect, actual)

    def test_valid_version_numbers(self):
        versions = [
            ('1.3.0', 1, 3, 0),
            ('2.1.1', 2, 1, 1),
            ('2.2.0dev', 2, 2, 0),
        ]

        for version in versions:
            ops = FakePostGISOperations(version[0])
            actual = ops.spatial_version
            self.assertEqual(version[1:], actual)

    def test_invalid_version_numbers(self):
        versions = ['nope', '123']

        for version in versions:
            ops = FakePostGISOperations(version)
            self.assertRaises(Exception, lambda: ops.spatial_version)

    def test_no_version_number(self):
        ops = FakePostGISOperations()
        self.assertRaises(ImproperlyConfigured, lambda: ops.spatial_version)
