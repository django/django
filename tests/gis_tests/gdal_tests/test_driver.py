import unittest

from django.contrib.gis.gdal import Driver, GDALException
from django.test import mock

valid_drivers = (
    # vector
    'ESRI Shapefile', 'MapInfo File', 'TIGER', 'S57', 'DGN', 'Memory', 'CSV',
    'GML', 'KML',
    # raster
    'GTiff', 'JPEG', 'MEM', 'PNG',
)

invalid_drivers = ('Foo baz', 'clucka', 'ESRI Shp', 'ESRI rast')

aliases = {
    'eSrI': 'ESRI Shapefile',
    'TigER/linE': 'TIGER',
    'SHAPE': 'ESRI Shapefile',
    'sHp': 'ESRI Shapefile',
    'tiFf': 'GTiff',
    'tIf': 'GTiff',
    'jPEg': 'JPEG',
    'jpG': 'JPEG',
}


class DriverTest(unittest.TestCase):

    def test01_valid_driver(self):
        "Testing valid GDAL/OGR Data Source Drivers."
        for d in valid_drivers:
            dr = Driver(d)
            self.assertEqual(d, str(dr))

    def test02_invalid_driver(self):
        "Testing invalid GDAL/OGR Data Source Drivers."
        for i in invalid_drivers:
            with self.assertRaises(GDALException):
                Driver(i)

    def test03_aliases(self):
        "Testing driver aliases."
        for alias, full_name in aliases.items():
            dr = Driver(alias)
            self.assertEqual(full_name, str(dr))

    @mock.patch('django.contrib.gis.gdal.driver.vcapi.get_driver_count')
    @mock.patch('django.contrib.gis.gdal.driver.rcapi.get_driver_count')
    @mock.patch('django.contrib.gis.gdal.driver.vcapi.register_all')
    @mock.patch('django.contrib.gis.gdal.driver.rcapi.register_all')
    def test_registered(self, rreg, vreg, rcount, vcount):
        """
        Prototypes are registered only if their respective driver counts are
        zero.
        """
        def check(rcount_val, vcount_val):
            vreg.reset_mock()
            rreg.reset_mock()
            rcount.return_value = rcount_val
            vcount.return_value = vcount_val
            Driver.ensure_registered()
            if rcount_val:
                self.assertFalse(rreg.called)
            else:
                rreg.assert_called_once_with()
            if vcount_val:
                self.assertFalse(vreg.called)
            else:
                vreg.assert_called_once_with()

        check(0, 0)
        check(120, 0)
        check(0, 120)
        check(120, 120)
