import unittest

from django.contrib.gis.gdal import GDAL_VERSION, gdal_full_version, gdal_version


class GDALTest(unittest.TestCase):
    def test_gdal_version(self):
        if GDAL_VERSION:
            expected = ("%s.%s.%s" % GDAL_VERSION).encode()
            self.assertIs(gdal_version().startswith(expected), True)
        else:
            self.assertIn(b".", gdal_version())

    def test_gdal_full_version(self):
        full_version = gdal_full_version()
        self.assertIn(gdal_version(), full_version)
        self.assertTrue(full_version.startswith(b"GDAL"))
