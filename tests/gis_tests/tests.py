import unittest

from django.core.exceptions import ImproperlyConfigured
from django.db import ProgrammingError

try:
    from django.contrib.gis.db.backends.postgis.operations import PostGISOperations
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
except ImproperlyConfigured as e:
    # If psycopg is installed but not geos, the import path hits
    # django.contrib.gis.geometry.backend which will "helpfully" convert
    # an ImportError into an ImproperlyConfigured.
    # Here, we make sure we're only catching this specific case and not another
    # ImproperlyConfigured one.
    if e.args and e.args[0].startswith('Could not import user-defined GEOMETRY_BACKEND'):
        HAS_POSTGRES = False
    else:
        raise


if HAS_POSTGRES:
    class FakeConnection:
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
            elif func == 'version':
                pass
            else:
                raise NotImplementedError('This function was not expected to be called')


@unittest.skipUnless(HAS_POSTGRES, "The psycopg2 driver is needed for these tests")
class TestPostGISVersionCheck(unittest.TestCase):
    """
    The PostGIS version check parses correctly the version numbers
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
            with self.assertRaises(Exception):
                ops.spatial_version

    def test_no_version_number(self):
        ops = FakePostGISOperations()
        with self.assertRaises(ImproperlyConfigured):
            ops.spatial_version

    def test_version_dependent_funcs(self):
        """
        Resolve names of functions renamed and deprecated in PostGIS 2.2.0
        depending on PostGIS version.
        Remove when dropping support for PostGIS 2.1.
        """
        ops = FakePostGISOperations('2.2.0')
        self.assertEqual(ops.spatial_function_name('DistanceSphere'), 'ST_DistanceSphere')
        self.assertEqual(ops.spatial_function_name('DistanceSpheroid'), 'ST_DistanceSpheroid')
        self.assertEqual(ops.spatial_function_name('LengthSpheroid'), 'ST_LengthSpheroid')
        self.assertEqual(ops.spatial_function_name('MemSize'), 'ST_MemSize')

        ops = FakePostGISOperations('2.1.0')
        self.assertEqual(ops.spatial_function_name('DistanceSphere'), 'ST_distance_sphere')
        self.assertEqual(ops.spatial_function_name('DistanceSpheroid'), 'ST_distance_spheroid')
        self.assertEqual(ops.spatial_function_name('LengthSpheroid'), 'ST_length_spheroid')
        self.assertEqual(ops.spatial_function_name('MemSize'), 'ST_mem_size')
