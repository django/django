"""
gdalinfo tests/gis_tests/data/rasters/raster.tif:

Driver: GTiff/GeoTIFF
Files: tests/gis_tests/data/rasters/raster.tif
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
import struct
import tempfile
import unittest

from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.shortcuts import numpy
from django.utils import six
from django.utils._os import upath

from ..data.rasters.textrasters import JSON_RASTER

if HAS_GDAL:
    from django.contrib.gis.gdal import GDALRaster, GDAL_VERSION
    from django.contrib.gis.gdal.raster.band import GDALBand


@unittest.skipUnless(HAS_GDAL, "GDAL is required")
class GDALRasterTests(unittest.TestCase):
    """
    Test a GDALRaster instance created from a file (GeoTiff).
    """
    def setUp(self):
        self.rs_path = os.path.join(os.path.dirname(upath(__file__)),
                                    '../data/rasters/raster.tif')
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
        # Assert correct values for file based raster
        self.assertEqual(self.rs.geotransform,
            [511700.4680706557, 100.0, 0.0, 435103.3771231986, 0.0, -100.0])
        self.assertEqual(self.rs.origin, [511700.4680706557, 435103.3771231986])
        self.assertEqual(self.rs.origin.x, 511700.4680706557)
        self.assertEqual(self.rs.origin.y, 435103.3771231986)
        self.assertEqual(self.rs.scale, [100.0, -100.0])
        self.assertEqual(self.rs.scale.x, 100.0)
        self.assertEqual(self.rs.scale.y, -100.0)
        self.assertEqual(self.rs.skew, [0, 0])
        self.assertEqual(self.rs.skew.x, 0)
        self.assertEqual(self.rs.skew.y, 0)
        # Create in-memory rasters and change gtvalues
        rsmem = GDALRaster(JSON_RASTER)
        rsmem.geotransform = range(6)
        self.assertEqual(rsmem.geotransform, [float(x) for x in range(6)])
        self.assertEqual(rsmem.origin, [0, 3])
        self.assertEqual(rsmem.origin.x, 0)
        self.assertEqual(rsmem.origin.y, 3)
        self.assertEqual(rsmem.scale, [1, 5])
        self.assertEqual(rsmem.scale.x, 1)
        self.assertEqual(rsmem.scale.y, 5)
        self.assertEqual(rsmem.skew, [2, 4])
        self.assertEqual(rsmem.skew.x, 2)
        self.assertEqual(rsmem.skew.y, 4)
        self.assertEqual(rsmem.width, 5)
        self.assertEqual(rsmem.height, 5)

    def test_rs_extent(self):
        self.assertEqual(self.rs.extent,
            (511700.4680706557, 417703.3771231986,
             528000.4680706557, 435103.3771231986))

    def test_rs_bands(self):
        self.assertEqual(len(self.rs.bands), 1)
        self.assertIsInstance(self.rs.bands[0], GDALBand)

    def test_memory_based_raster_creation(self):
        # Create uint8 raster with full pixel data range (0-255)
        rast = GDALRaster({
            'datatype': 1,
            'width': 16,
            'height': 16,
            'srid': 4326,
            'bands': [{
                'data': range(256),
                'nodata_value': 255,
            }],
        })

        # Get array from raster
        result = rast.bands[0].data()
        if numpy:
            result = result.flatten().tolist()

        # Assert data is same as original input
        self.assertEqual(result, list(range(256)))

    def test_file_based_raster_creation(self):
        # Prepare tempfile
        rstfile = tempfile.NamedTemporaryFile(suffix='.tif')

        # Create file-based raster from scratch
        GDALRaster({
            'datatype': self.rs.bands[0].datatype(),
            'driver': 'tif',
            'name': rstfile.name,
            'width': 163,
            'height': 174,
            'nr_of_bands': 1,
            'srid': self.rs.srs.wkt,
            'origin': (self.rs.origin.x, self.rs.origin.y),
            'scale': (self.rs.scale.x, self.rs.scale.y),
            'skew': (self.rs.skew.x, self.rs.skew.y),
            'bands': [{
                'data': self.rs.bands[0].data(),
                'nodata_value': self.rs.bands[0].nodata_value,
            }],
        })

        # Reload newly created raster from file
        restored_raster = GDALRaster(rstfile.name)
        self.assertEqual(restored_raster.srs.wkt, self.rs.srs.wkt)
        self.assertEqual(restored_raster.geotransform, self.rs.geotransform)
        if numpy:
            numpy.testing.assert_equal(
                restored_raster.bands[0].data(),
                self.rs.bands[0].data()
            )
        else:
            self.assertEqual(restored_raster.bands[0].data(), self.rs.bands[0].data())

    def test_raster_warp(self):
        # Create in memory raster
        source = GDALRaster({
            'datatype': 1,
            'driver': 'MEM',
            'name': 'sourceraster',
            'width': 4,
            'height': 4,
            'nr_of_bands': 1,
            'srid': 3086,
            'origin': (500000, 400000),
            'scale': (100, -100),
            'skew': (0, 0),
            'bands': [{
                'data': range(16),
                'nodata_value': 255,
            }],
        })

        # Test altering the scale, width, and height of a raster
        data = {
            'scale': [200, -200],
            'width': 2,
            'height': 2,
        }
        target = source.warp(data)
        self.assertEqual(target.width, data['width'])
        self.assertEqual(target.height, data['height'])
        self.assertEqual(target.scale, data['scale'])
        self.assertEqual(target.bands[0].datatype(), source.bands[0].datatype())
        self.assertEqual(target.name, 'sourceraster_copy.MEM')
        result = target.bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        self.assertEqual(result, [5, 7, 13, 15])

        # Test altering the name and datatype (to float)
        data = {
            'name': '/path/to/targetraster.tif',
            'datatype': 6,
        }
        target = source.warp(data)
        self.assertEqual(target.bands[0].datatype(), 6)
        self.assertEqual(target.name, '/path/to/targetraster.tif')
        self.assertEqual(target.driver.name, 'MEM')
        result = target.bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        self.assertEqual(
            result,
            [0.0, 1.0, 2.0, 3.0,
             4.0, 5.0, 6.0, 7.0,
             8.0, 9.0, 10.0, 11.0,
             12.0, 13.0, 14.0, 15.0]
        )

    def test_raster_transform(self):
        if GDAL_VERSION < (1, 8, 1):
            self.skipTest("GDAL >= 1.8.1 is required for this test")
        # Prepare tempfile and nodata value
        rstfile = tempfile.NamedTemporaryFile(suffix='.tif')
        ndv = 99

        # Create in file based raster
        source = GDALRaster({
            'datatype': 1,
            'driver': 'tif',
            'name': rstfile.name,
            'width': 5,
            'height': 5,
            'nr_of_bands': 1,
            'srid': 4326,
            'origin': (-5, 5),
            'scale': (2, -2),
            'skew': (0, 0),
            'bands': [{
                'data': range(25),
                'nodata_value': ndv,
            }],
        })

        # Transform raster into srid 4326.
        target = source.transform(3086)

        # Reload data from disk
        target = GDALRaster(target.name)

        self.assertEqual(target.srs.srid, 3086)
        self.assertEqual(target.width, 7)
        self.assertEqual(target.height, 7)
        self.assertEqual(target.bands[0].datatype(), source.bands[0].datatype())
        self.assertEqual(target.origin, [9124842.791079799, 1589911.6476407414])
        self.assertEqual(target.scale, [223824.82664250192, -223824.82664250192])
        self.assertEqual(target.skew, [0, 0])

        result = target.bands[0].data()
        if numpy:
            result = result.flatten().tolist()

        # The reprojection of a raster that spans over a large area
        # skews the data matrix and might introduce nodata values.
        self.assertEqual(
            result,
            [
                ndv, ndv, ndv, ndv, 4, ndv, ndv,
                ndv, ndv, 2, 3, 9, ndv, ndv,
                ndv, 1, 2, 8, 13, 19, ndv,
                0, 6, 6, 12, 18, 18, 24,
                ndv, 10, 11, 16, 22, 23, ndv,
                ndv, ndv, 15, 21, 22, ndv, ndv,
                ndv, ndv, 20, ndv, ndv, ndv, ndv,
            ]
        )


@unittest.skipUnless(HAS_GDAL, "GDAL is required")
class GDALBandTests(unittest.TestCase):
    def setUp(self):
        self.rs_path = os.path.join(os.path.dirname(upath(__file__)),
                               '../data/rasters/raster.tif')
        rs = GDALRaster(self.rs_path)
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

    def test_read_mode_error(self):
        # Open raster in read mode
        rs = GDALRaster(self.rs_path, write=False)
        band = rs.bands[0]

        # Setting attributes in write mode raises exception in the _flush method
        self.assertRaises(GDALException, setattr, band, 'nodata_value', 10)

    def test_band_data_setters(self):
        # Create in-memory raster and get band
        rsmem = GDALRaster({
            'datatype': 1,
            'driver': 'MEM',
            'name': 'mem_rst',
            'width': 10,
            'height': 10,
            'nr_of_bands': 1,
            'srid': 4326,
        })
        bandmem = rsmem.bands[0]

        # Set nodata value
        bandmem.nodata_value = 99
        self.assertEqual(bandmem.nodata_value, 99)

        # Set data for entire dataset
        bandmem.data(range(100))
        if numpy:
            numpy.testing.assert_equal(bandmem.data(), numpy.arange(100).reshape(10, 10))
        else:
            self.assertEqual(bandmem.data(), list(range(100)))

        # Prepare data for setting values in subsequent tests
        block = list(range(100, 104))
        packed_block = struct.pack('<' + 'B B B B', *block)

        # Set data from list
        bandmem.data(block, (1, 1), (2, 2))
        result = bandmem.data(offset=(1, 1), size=(2, 2))
        if numpy:
            numpy.testing.assert_equal(result, numpy.array(block).reshape(2, 2))
        else:
            self.assertEqual(result, block)

        # Set data from packed block
        bandmem.data(packed_block, (1, 1), (2, 2))
        result = bandmem.data(offset=(1, 1), size=(2, 2))
        if numpy:
            numpy.testing.assert_equal(result, numpy.array(block).reshape(2, 2))
        else:
            self.assertEqual(result, block)

        # Set data from bytes
        bandmem.data(bytes(packed_block), (1, 1), (2, 2))
        result = bandmem.data(offset=(1, 1), size=(2, 2))
        if numpy:
            numpy.testing.assert_equal(result, numpy.array(block).reshape(2, 2))
        else:
            self.assertEqual(result, block)

        # Set data from bytearray
        bandmem.data(bytearray(packed_block), (1, 1), (2, 2))
        result = bandmem.data(offset=(1, 1), size=(2, 2))
        if numpy:
            numpy.testing.assert_equal(result, numpy.array(block).reshape(2, 2))
        else:
            self.assertEqual(result, block)

        # Set data from memoryview
        bandmem.data(six.memoryview(packed_block), (1, 1), (2, 2))
        result = bandmem.data(offset=(1, 1), size=(2, 2))
        if numpy:
            numpy.testing.assert_equal(result, numpy.array(block).reshape(2, 2))
        else:
            self.assertEqual(result, block)

        # Set data from numpy array
        if numpy:
            bandmem.data(numpy.array(block, dtype='int8').reshape(2, 2), (1, 1), (2, 2))
            numpy.testing.assert_equal(
                bandmem.data(offset=(1, 1), size=(2, 2)),
                numpy.array(block).reshape(2, 2)
            )

        # Test json input data
        rsmemjson = GDALRaster(JSON_RASTER)
        bandmemjson = rsmemjson.bands[0]
        if numpy:
            numpy.testing.assert_equal(
                bandmemjson.data(),
                numpy.array(range(25)).reshape(5, 5)
            )
        else:
            self.assertEqual(bandmemjson.data(), list(range(25)))
