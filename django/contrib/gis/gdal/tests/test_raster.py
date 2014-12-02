"""
gdalinfo django/contrib/gis/gdal/tests/data/raster.tif:

Driver: GTiff/GeoTIFF
Files: django/contrib/gis/gdal/tests/data/raster.tif
Size is 163, 174
Coordinate System is:
PROJCS["NAD83 / Florida GDL Albers",
    GEOGCS["NAD83",
        DATUM["North_American_Datum_1983",
            SPHEROID["GRS 1980",6378137,298.2572221010002,
                AUTHORITY["EPSG","7019"]],
            TOWGS84[0,0,0,0,0,0,0],
            AUTHORITY["EPSG","6269"]],
        PRIMEM["Greenwich",0],
        UNIT["degree",0.0174532925199433],
        AUTHORITY["EPSG","4269"]],
    PROJECTION["Albers_Conic_Equal_Area"],
    PARAMETER["standard_parallel_1",24],
    PARAMETER["standard_parallel_2",31.5],
    PARAMETER["latitude_of_center",24],
    PARAMETER["longitude_of_center",-84],
    PARAMETER["false_easting",400000],
    PARAMETER["false_northing",0],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    AUTHORITY["EPSG","3086"]]
Origin = (511700.468070655711927,435103.377123198588379)
Pixel Size = (100.000000000000000,-100.000000000000000)
Metadata:
  AREA_OR_POINT=Area
Image Structure Metadata:
  INTERLEAVE=BAND
Corner Coordinates:
Upper Left  (  511700.468,  435103.377) ( 82d51'46.16"W, 27d55' 1.53"N)
Lower Left  (  511700.468,  417703.377) ( 82d51'52.04"W, 27d45'37.50"N)
Upper Right (  528000.468,  435103.377) ( 82d41'48.81"W, 27d54'56.30"N)
Lower Right (  528000.468,  417703.377) ( 82d41'55.54"W, 27d45'32.28"N)
Center      (  519850.468,  426403.377) ( 82d46'50.64"W, 27d50'16.99"N)
Band 1 Block=163x50 Type=Byte, ColorInterp=Gray
  NoData Value=15
"""
import os
import unittest

from django.contrib.gis.gdal import HAS_GDAL
from django.utils import six
from django.utils._os import upath

if HAS_GDAL:
    from django.contrib.gis.gdal import GDALRaster
    from django.contrib.gis.gdal.raster.band import GDALBand


@unittest.skipUnless(HAS_GDAL, "GDAL is required")
class GDALRasterTests(unittest.TestCase):
    """
    Test a GDALRaster instance created from a file (GeoTiff).
    """
    def setUp(self):
        self.rs_path = os.path.join(os.path.dirname(upath(__file__)),
                                    'data/raster.tif')
        self.rs = GDALRaster(self.rs_path)

    def test_rs_name_repr(self):
        self.assertEqual(self.rs_path, self.rs.name)
        six.assertRegex(self, repr(self.rs), "<Raster object at 0x\w+>")

    def test_rs_driver(self):
        self.assertEqual(self.rs.driver.name, 'GTiff')

    def test_rs_size(self):
        self.assertEqual(self.rs.width, 163)
        self.assertEqual(self.rs.height, 174)

    def test_rs_srs(self):
        self.assertEqual(self.rs.srs.srid, 3086)
        self.assertEqual(self.rs.srs.units, (1.0, 'metre'))

    def test_geotransform_and_friends(self):
        self.assertEqual(self.rs.geotransform,
            (511700.4680706557, 100.0, 0.0, 435103.3771231986, 0.0, -100.0))
        self.assertEqual(self.rs.origin, [511700.4680706557, 435103.3771231986])
        self.assertEqual(self.rs.origin.x, 511700.4680706557)
        self.assertEqual(self.rs.origin.y, 435103.3771231986)
        self.assertEqual(self.rs.scale, [100.0, -100.0])
        self.assertEqual(self.rs.scale.x, 100.0)
        self.assertEqual(self.rs.scale.y, -100.0)
        self.assertEqual(self.rs.skew, [0, 0])
        self.assertEqual(self.rs.skew.x, 0)
        self.assertEqual(self.rs.skew.y, 0)

    def test_rs_extent(self):
        self.assertEqual(self.rs.extent,
            (511700.4680706557, 417703.3771231986, 528000.4680706557, 435103.3771231986))

    def test_rs_bands(self):
        self.assertEqual(len(self.rs.bands), 1)
        self.assertIsInstance(self.rs.bands[0], GDALBand)


@unittest.skipUnless(HAS_GDAL, "GDAL is required")
class GDALBandTests(unittest.TestCase):
    def setUp(self):
        rs_path = os.path.join(os.path.dirname(upath(__file__)),
                               'data/raster.tif')
        rs = GDALRaster(rs_path)
        self.band = rs.bands[0]

    def test_band_data(self):
        self.assertEqual(self.band.width, 163)
        self.assertEqual(self.band.height, 174)
        self.assertEqual(self.band.description, '')
        self.assertEqual(self.band.datatype(), 1)
        self.assertEqual(self.band.datatype(as_string=True), 'GDT_Byte')
        self.assertEqual(self.band.min, 0)
        self.assertEqual(self.band.max, 255)
        self.assertEqual(self.band.nodata_value, 15)
