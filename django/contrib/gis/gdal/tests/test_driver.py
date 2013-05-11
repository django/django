from django.contrib.gis.gdal import HAS_GDAL
from django.utils import unittest
from django.utils.unittest import skipUnless

if HAS_GDAL:
    from django.contrib.gis.gdal import Driver, OGRException


valid_drivers = ('ESRI Shapefile', 'MapInfo File', 'TIGER', 'S57', 'DGN',
                 'Memory', 'CSV', 'GML', 'KML')

invalid_drivers = ('Foo baz', 'clucka', 'ESRI Shp')

aliases = {'eSrI' : 'ESRI Shapefile',
           'TigER/linE' : 'TIGER',
           'SHAPE' : 'ESRI Shapefile',
           'sHp' : 'ESRI Shapefile',
           }


@skipUnless(HAS_GDAL, "GDAL is required")
class DriverTest(unittest.TestCase):

    def test01_valid_driver(self):
        "Testing valid OGR Data Source Drivers."
        for d in valid_drivers:
            dr = Driver(d)
            self.assertEqual(d, str(dr))

    def test02_invalid_driver(self):
        "Testing invalid OGR Data Source Drivers."
        for i in invalid_drivers:
            self.assertRaises(OGRException, Driver, i)

    def test03_aliases(self):
        "Testing driver aliases."
        for alias, full_name in aliases.items():
            dr = Driver(alias)
            self.assertEqual(full_name, str(dr))
