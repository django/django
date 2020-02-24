import unittest

from django.contrib.gis.gdal import GDAL_VERSION, gdal_version


class GDALTest(unittest.TestCase):
    def test_gdal_version(self):
        if GDAL_VERSION:
            self.assertEqual(gdal_version(), ('%s.%s.%s' % GDAL_VERSION).encode())
        else:
            self.assertIn(b'.', gdal_version())
