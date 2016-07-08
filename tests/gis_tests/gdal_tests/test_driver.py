import unittest

from django.contrib.gis.gdal import HAS_GDAL

if HAS_GDAL:
    from django.contrib.gis.gdal import Driver, GDALException


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


@unittest.skipUnless(HAS_GDAL, "GDAL is required")
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
