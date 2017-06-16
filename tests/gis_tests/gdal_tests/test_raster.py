import os
import struct
import tempfile

from django.contrib.gis.gdal import GDAL_VERSION, GDALRaster
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.raster.band import GDALBand
from django.contrib.gis.shortcuts import numpy
from django.test import SimpleTestCase

from ..data.rasters.textrasters import JSON_RASTER


class GDALRasterTests(SimpleTestCase):
    """
    Test a GDALRaster instance created from a file (GeoTiff).
    """
    def setUp(self):
        self.rs_path = os.path.join(os.path.dirname(__file__), '../data/rasters/raster.tif')
        self.rs = GDALRaster(self.rs_path)

    def test_rs_name_repr(self):
        self.assertEqual(self.rs_path, self.rs.name)
        self.assertRegex(repr(self.rs), r"<Raster object at 0x\w+>")

    def test_rs_driver(self):
        self.assertEqual(self.rs.driver.name, 'GTiff')

    def test_rs_size(self):
        self.assertEqual(self.rs.width, 163)
        self.assertEqual(self.rs.height, 174)

    def test_rs_srs(self):
        self.assertEqual(self.rs.srs.srid, 3086)
        self.assertEqual(self.rs.srs.units, (1.0, 'metre'))

    def test_rs_srid(self):
        rast = GDALRaster({
            'width': 16,
            'height': 16,
            'srid': 4326,
        })
        self.assertEqual(rast.srid, 4326)
        rast.srid = 3086
        self.assertEqual(rast.srid, 3086)

    def test_geotransform_and_friends(self):
        # Assert correct values for file based raster
        self.assertEqual(
            self.rs.geotransform,
            [511700.4680706557, 100.0, 0.0, 435103.3771231986, 0.0, -100.0]
        )
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
        # geotransform accepts both floats and ints
        rsmem.geotransform = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(rsmem.geotransform, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
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

    def test_geotransform_bad_inputs(self):
        rsmem = GDALRaster(JSON_RASTER)
        error_geotransforms = [
            [1, 2],
            [1, 2, 3, 4, 5, 'foo'],
            [1, 2, 3, 4, 5, 6, 'foo'],
        ]
        msg = 'Geotransform must consist of 6 numeric values.'
        for geotransform in error_geotransforms:
            with self.subTest(i=geotransform), self.assertRaisesMessage(ValueError, msg):
                rsmem.geotransform = geotransform

    def test_rs_extent(self):
        self.assertEqual(
            self.rs.extent,
            (511700.4680706557, 417703.3771231986, 528000.4680706557, 435103.3771231986)
        )

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

    def test_vsi_raster_creation(self):
        # Open a raster as a file object.
        with open(self.rs_path, 'rb') as dat:
            # Instantiate a raster from the file binary buffer.
            vsimem = GDALRaster(dat.read())
        # The data of the in-memory file is equal to the source file.
        result = vsimem.bands[0].data()
        target = self.rs.bands[0].data()
        if numpy:
            result = result.flatten().tolist()
            target = target.flatten().tolist()
        self.assertEqual(result, target)

    def test_vsi_raster_deletion(self):
        path = '/vsimem/raster.tif'
        # Create a vsi-based raster from scratch.
        vsimem = GDALRaster({
            'name': path,
            'driver': 'tif',
            'width': 4,
            'height': 4,
            'srid': 4326,
            'bands': [{
                'data': range(16),
            }],
        })
        # The virtual file exists.
        rst = GDALRaster(path)
        self.assertEqual(rst.width, 4)
        # Delete GDALRaster.
        del vsimem
        del rst
        # The virtual file has been removed.
        msg = 'Could not open the datasource at "/vsimem/raster.tif"'
        with self.assertRaisesMessage(GDALException, msg):
            GDALRaster(path)

    def test_vsi_invalid_buffer_error(self):
        msg = 'Failed creating VSI raster from the input buffer.'
        with self.assertRaisesMessage(GDALException, msg):
            GDALRaster(b'not-a-raster-buffer')

    def test_vsi_buffer_property(self):
        # Create a vsi-based raster from scratch.
        rast = GDALRaster({
            'name': '/vsimem/raster.tif',
            'driver': 'tif',
            'width': 4,
            'height': 4,
            'srid': 4326,
            'bands': [{
                'data': range(16),
            }],
        })
        # Do a round trip from raster to buffer to raster.
        result = GDALRaster(rast.vsi_buffer).bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        # Band data is equal to nodata value except on input block of ones.
        self.assertEqual(result, list(range(16)))
        # The vsi buffer is None for rasters that are not vsi based.
        self.assertIsNone(self.rs.vsi_buffer)

    def test_offset_size_and_shape_on_raster_creation(self):
        rast = GDALRaster({
            'datatype': 1,
            'width': 4,
            'height': 4,
            'srid': 4326,
            'bands': [{
                'data': (1,),
                'offset': (1, 1),
                'size': (2, 2),
                'shape': (1, 1),
                'nodata_value': 2,
            }],
        })
        # Get array from raster.
        result = rast.bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        # Band data is equal to nodata value except on input block of ones.
        self.assertEqual(
            result,
            [2, 2, 2, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2, 2, 2, 2]
        )

    def test_set_nodata_value_on_raster_creation(self):
        # Create raster filled with nodata values.
        rast = GDALRaster({
            'datatype': 1,
            'width': 2,
            'height': 2,
            'srid': 4326,
            'bands': [{'nodata_value': 23}],
        })
        # Get array from raster.
        result = rast.bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        # All band data is equal to nodata value.
        self.assertEqual(result, [23, ] * 4)

    def test_set_nodata_none_on_raster_creation(self):
        if GDAL_VERSION < (2, 1):
            self.skipTest("GDAL >= 2.1 is required for this test.")
        # Create raster without data and without nodata value.
        rast = GDALRaster({
            'datatype': 1,
            'width': 2,
            'height': 2,
            'srid': 4326,
            'bands': [{'nodata_value': None}],
        })
        # Get array from raster.
        result = rast.bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        # Band data is equal to zero becaues no nodata value has been specified.
        self.assertEqual(result, [0] * 4)

    def test_raster_metadata_property(self):
        # Check for required gdal version.
        if GDAL_VERSION < (1, 11):
            msg = 'GDAL ≥ 1.11 is required for using the metadata property.'
            with self.assertRaisesMessage(ValueError, msg):
                self.rs.metadata
            return

        self.assertEqual(
            self.rs.metadata,
            {'DEFAULT': {'AREA_OR_POINT': 'Area'}, 'IMAGE_STRUCTURE': {'INTERLEAVE': 'BAND'}},
        )

        # Create file-based raster from scratch
        source = GDALRaster({
            'datatype': 1,
            'width': 2,
            'height': 2,
            'srid': 4326,
            'bands': [{'data': range(4), 'nodata_value': 99}],
        })
        # Set metadata on raster and on a band.
        metadata = {
            'DEFAULT': {'OWNER': 'Django', 'VERSION': '1.0', 'AREA_OR_POINT': 'Point', },
        }
        source.metadata = metadata
        source.bands[0].metadata = metadata
        self.assertEqual(source.metadata['DEFAULT'], metadata['DEFAULT'])
        self.assertEqual(source.bands[0].metadata['DEFAULT'], metadata['DEFAULT'])
        # Update metadata on raster.
        metadata = {
            'DEFAULT': {'VERSION': '2.0', },
        }
        source.metadata = metadata
        self.assertEqual(source.metadata['DEFAULT']['VERSION'], '2.0')
        # Remove metadata on raster.
        metadata = {
            'DEFAULT': {'OWNER': None, },
        }
        source.metadata = metadata
        self.assertNotIn('OWNER', source.metadata['DEFAULT'])

    def test_raster_info_accessor(self):
        if GDAL_VERSION < (2, 1):
            msg = 'GDAL ≥ 2.1 is required for using the info property.'
            with self.assertRaisesMessage(ValueError, msg):
                self.rs.info
            return
        gdalinfo = """
        Driver: GTiff/GeoTIFF
        Files: {0}
        Size is 163, 174
        Coordinate System is:
        PROJCS["NAD83 / Florida GDL Albers",
            GEOGCS["NAD83",
                DATUM["North_American_Datum_1983",
                    SPHEROID["GRS 1980",6378137,298.257222101,
                        AUTHORITY["EPSG","7019"]],
                    TOWGS84[0,0,0,0,0,0,0],
                    AUTHORITY["EPSG","6269"]],
                PRIMEM["Greenwich",0,
                    AUTHORITY["EPSG","8901"]],
                UNIT["degree",0.0174532925199433,
                    AUTHORITY["EPSG","9122"]],
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
            AXIS["X",EAST],
            AXIS["Y",NORTH],
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
        """.format(self.rs_path)
        # Data
        info_dyn = [line.strip() for line in self.rs.info.split('\n') if line.strip() != '']
        info_ref = [line.strip() for line in gdalinfo.split('\n') if line.strip() != '']
        self.assertEqual(info_dyn, info_ref)

    def test_compressed_file_based_raster_creation(self):
        rstfile = tempfile.NamedTemporaryFile(suffix='.tif')
        # Make a compressed copy of an existing raster.
        compressed = self.rs.warp({'papsz_options': {'compress': 'packbits'}, 'name': rstfile.name})
        # Check physically if compression worked.
        self.assertLess(os.path.getsize(compressed.name), os.path.getsize(self.rs.name))
        if GDAL_VERSION > (1, 11):
            # Create file-based raster with options from scratch.
            compressed = GDALRaster({
                'datatype': 1,
                'driver': 'tif',
                'name': rstfile.name,
                'width': 40,
                'height': 40,
                'srid': 3086,
                'origin': (500000, 400000),
                'scale': (100, -100),
                'skew': (0, 0),
                'bands': [{
                    'data': range(40 ^ 2),
                    'nodata_value': 255,
                }],
                'papsz_options': {
                    'compress': 'packbits',
                    'pixeltype': 'signedbyte',
                    'blockxsize': 23,
                    'blockysize': 23,
                }
            })
            # Check if options used on creation are stored in metadata.
            # Reopening the raster ensures that all metadata has been written
            # to the file.
            compressed = GDALRaster(compressed.name)
            self.assertEqual(compressed.metadata['IMAGE_STRUCTURE']['COMPRESSION'], 'PACKBITS',)
            self.assertEqual(compressed.bands[0].metadata['IMAGE_STRUCTURE']['PIXELTYPE'], 'SIGNEDBYTE')
            if GDAL_VERSION >= (2, 1):
                self.assertIn('Block=40x23', compressed.info)

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

    def test_raster_warp_nodata_zone(self):
        # Create in memory raster.
        source = GDALRaster({
            'datatype': 1,
            'driver': 'MEM',
            'width': 4,
            'height': 4,
            'srid': 3086,
            'origin': (500000, 400000),
            'scale': (100, -100),
            'skew': (0, 0),
            'bands': [{
                'data': range(16),
                'nodata_value': 23,
            }],
        })
        # Warp raster onto a location that does not cover any pixels of the original.
        result = source.warp({'origin': (200000, 200000)}).bands[0].data()
        if numpy:
            result = result.flatten().tolist()
        # The result is an empty raster filled with the correct nodata value.
        self.assertEqual(result, [23] * 16)

    def test_raster_transform(self):
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
        self.assertAlmostEqual(target.origin[0], 9124842.791079799)
        self.assertAlmostEqual(target.origin[1], 1589911.6476407414)
        self.assertAlmostEqual(target.scale[0], 223824.82664250192)
        self.assertAlmostEqual(target.scale[1], -223824.82664250192)
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


class GDALBandTests(SimpleTestCase):
    def setUp(self):
        self.rs_path = os.path.join(os.path.dirname(__file__), '../data/rasters/raster.tif')
        rs = GDALRaster(self.rs_path)
        self.band = rs.bands[0]

    def test_band_data(self):
        pam_file = self.rs_path + '.aux.xml'
        self.assertEqual(self.band.width, 163)
        self.assertEqual(self.band.height, 174)
        self.assertEqual(self.band.description, '')
        self.assertEqual(self.band.datatype(), 1)
        self.assertEqual(self.band.datatype(as_string=True), 'GDT_Byte')
        self.assertEqual(self.band.nodata_value, 15)
        if numpy:
            data = self.band.data()
            assert_array = numpy.loadtxt(
                os.path.join(os.path.dirname(__file__), '../data/rasters/raster.numpy.txt')
            )
            numpy.testing.assert_equal(data, assert_array)
            self.assertEqual(data.shape, (self.band.height, self.band.width))
        try:
            smin, smax, smean, sstd = self.band.statistics(approximate=True)
            self.assertEqual(smin, 0)
            self.assertEqual(smax, 9)
            self.assertAlmostEqual(smean, 2.842331288343558)
            self.assertAlmostEqual(sstd, 2.3965567248965356)

            smin, smax, smean, sstd = self.band.statistics(approximate=False, refresh=True)
            self.assertEqual(smin, 0)
            self.assertEqual(smax, 9)
            self.assertAlmostEqual(smean, 2.828326634228898)
            self.assertAlmostEqual(sstd, 2.4260526986669095)

            self.assertEqual(self.band.min, 0)
            self.assertEqual(self.band.max, 9)
            self.assertAlmostEqual(self.band.mean, 2.828326634228898)
            self.assertAlmostEqual(self.band.std, 2.4260526986669095)

            # Statistics are persisted into PAM file on band close
            self.band = None
            self.assertTrue(os.path.isfile(pam_file))
        finally:
            # Close band and remove file if created
            self.band = None
            if os.path.isfile(pam_file):
                os.remove(pam_file)

    def test_read_mode_error(self):
        # Open raster in read mode
        rs = GDALRaster(self.rs_path, write=False)
        band = rs.bands[0]

        # Setting attributes in write mode raises exception in the _flush method
        with self.assertRaises(GDALException):
            setattr(band, 'nodata_value', 10)

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
        bandmem.data(memoryview(packed_block), (1, 1), (2, 2))
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

    def test_band_statistics_automatic_refresh(self):
        rsmem = GDALRaster({
            'srid': 4326,
            'width': 2,
            'height': 2,
            'bands': [{'data': [0] * 4, 'nodata_value': 99}],
        })
        band = rsmem.bands[0]
        # Populate statistics cache
        self.assertEqual(band.statistics(), (0, 0, 0, 0))
        # Change data
        band.data([1, 1, 0, 0])
        # Statistics are properly updated
        self.assertEqual(band.statistics(), (0.0, 1.0, 0.5, 0.5))
        # Change nodata_value
        band.nodata_value = 0
        # Statistics are properly updated
        self.assertEqual(band.statistics(), (1.0, 1.0, 1.0, 0.0))

    def test_band_statistics_empty_band(self):
        rsmem = GDALRaster({
            'srid': 4326,
            'width': 1,
            'height': 1,
            'bands': [{'data': [0], 'nodata_value': 0}],
        })
        self.assertEqual(rsmem.bands[0].statistics(), (None, None, None, None))

    def test_band_delete_nodata(self):
        rsmem = GDALRaster({
            'srid': 4326,
            'width': 1,
            'height': 1,
            'bands': [{'data': [0], 'nodata_value': 1}],
        })
        if GDAL_VERSION < (2, 1):
            msg = 'GDAL >= 2.1 required to delete nodata values.'
            with self.assertRaisesMessage(ValueError, msg):
                rsmem.bands[0].nodata_value = None
        else:
            rsmem.bands[0].nodata_value = None
            self.assertIsNone(rsmem.bands[0].nodata_value)

    def test_band_data_replication(self):
        band = GDALRaster({
            'srid': 4326,
            'width': 3,
            'height': 3,
            'bands': [{'data': range(10, 19), 'nodata_value': 0}],
        }).bands[0]

        # Variations for input (data, shape, expected result).
        combos = (
            ([1], (1, 1), [1] * 9),
            (range(3), (1, 3), [0, 0, 0, 1, 1, 1, 2, 2, 2]),
            (range(3), (3, 1), [0, 1, 2, 0, 1, 2, 0, 1, 2]),
        )
        for combo in combos:
            band.data(combo[0], shape=combo[1])
            if numpy:
                numpy.testing.assert_equal(band.data(), numpy.array(combo[2]).reshape(3, 3))
            else:
                self.assertEqual(band.data(), list(combo[2]))
