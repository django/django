import os
import unittest
from unittest import skipUnless

from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.geometry.test_data import get_ds_file, TestDS, TEST_DATA

if HAS_GDAL:
    from django.contrib.gis.gdal import DataSource, Envelope, OGRGeometry, OGRException, OGRIndexError, GDAL_VERSION
    from django.contrib.gis.gdal.field import OFTReal, OFTInteger, OFTString

    # List of acceptable data sources.
    ds_list = (
        TestDS('test_point', nfeat=5, nfld=3, geom='POINT', gtype=1, driver='ESRI Shapefile',
            fields={'dbl': OFTReal, 'int': OFTInteger, 'str': OFTString},
            extent=(-1.35011, 0.166623, -0.524093, 0.824508),  # Got extent from QGIS
            srs_wkt='GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]',
            field_values={'dbl': [float(i) for i in range(1, 6)], 'int': list(range(1, 6)), 'str': [str(i) for i in range(1, 6)]},
            fids=range(5)),
        TestDS('test_vrt', ext='vrt', nfeat=3, nfld=3, geom='POINT', gtype='Point25D', driver='VRT',
            fields={'POINT_X': OFTString, 'POINT_Y': OFTString, 'NUM': OFTString},  # VRT uses CSV, which all types are OFTString.
            extent=(1.0, 2.0, 100.0, 523.5),  # Min/Max from CSV
            field_values={'POINT_X': ['1.0', '5.0', '100.0'], 'POINT_Y': ['2.0', '23.0', '523.5'], 'NUM': ['5', '17', '23']},
            fids=range(1, 4)),
        TestDS('test_poly', nfeat=3, nfld=3, geom='POLYGON', gtype=3,
            driver='ESRI Shapefile',
            fields={'float': OFTReal, 'int': OFTInteger, 'str': OFTString},
            extent=(-1.01513, -0.558245, 0.161876, 0.839637),  # Got extent from QGIS
            srs_wkt='GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'),
    )

bad_ds = (TestDS('foo'),)


@skipUnless(HAS_GDAL, "GDAL is required")
class DataSourceTest(unittest.TestCase):

    def test01_valid_shp(self):
        "Testing valid SHP Data Source files."

        for source in ds_list:
            # Loading up the data source
            ds = DataSource(source.ds)

            # Making sure the layer count is what's expected (only 1 layer in a SHP file)
            self.assertEqual(1, len(ds))

            # Making sure GetName works
            self.assertEqual(source.ds, ds.name)

            # Making sure the driver name matches up
            self.assertEqual(source.driver, str(ds.driver))

            # Making sure indexing works
            try:
                ds[len(ds)]
            except OGRIndexError:
                pass
            else:
                self.fail('Expected an IndexError!')

    def test02_invalid_shp(self):
        "Testing invalid SHP files for the Data Source."
        for source in bad_ds:
            self.assertRaises(OGRException, DataSource, source.ds)

    def test03a_layers(self):
        "Testing Data Source Layers."
        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer, this tests DataSource.__iter__
            for layer in ds:
                # Making sure we get the number of features we expect
                self.assertEqual(len(layer), source.nfeat)

                # Making sure we get the number of fields we expect
                self.assertEqual(source.nfld, layer.num_fields)
                self.assertEqual(source.nfld, len(layer.fields))

                # Testing the layer's extent (an Envelope), and its properties
                if source.driver == 'VRT' and (GDAL_VERSION >= (1, 7, 0) and GDAL_VERSION < (1, 7, 3)):
                    # There's a known GDAL regression with retrieving the extent
                    # of a VRT layer in versions 1.7.0-1.7.2:
                    #  http://trac.osgeo.org/gdal/ticket/3783
                    pass
                else:
                    self.assertEqual(True, isinstance(layer.extent, Envelope))
                    self.assertAlmostEqual(source.extent[0], layer.extent.min_x, 5)
                    self.assertAlmostEqual(source.extent[1], layer.extent.min_y, 5)
                    self.assertAlmostEqual(source.extent[2], layer.extent.max_x, 5)
                    self.assertAlmostEqual(source.extent[3], layer.extent.max_y, 5)

                # Now checking the field names.
                flds = layer.fields
                for f in flds:
                    self.assertEqual(True, f in source.fields)

                # Negative FIDs are not allowed.
                self.assertRaises(OGRIndexError, layer.__getitem__, -1)
                self.assertRaises(OGRIndexError, layer.__getitem__, 50000)

                if hasattr(source, 'field_values'):
                    fld_names = source.field_values.keys()

                    # Testing `Layer.get_fields` (which uses Layer.__iter__)
                    for fld_name in fld_names:
                        self.assertEqual(source.field_values[fld_name], layer.get_fields(fld_name))

                    # Testing `Layer.__getitem__`.
                    for i, fid in enumerate(source.fids):
                        feat = layer[fid]
                        self.assertEqual(fid, feat.fid)
                        # Maybe this should be in the test below, but we might as well test
                        # the feature values here while in this loop.
                        for fld_name in fld_names:
                            self.assertEqual(source.field_values[fld_name][i], feat.get(fld_name))

    def test03b_layer_slice(self):
        "Test indexing and slicing on Layers."
        # Using the first data-source because the same slice
        # can be used for both the layer and the control values.
        source = ds_list[0]
        ds = DataSource(source.ds)

        sl = slice(1, 3)
        feats = ds[0][sl]

        for fld_name in ds[0].fields:
            test_vals = [feat.get(fld_name) for feat in feats]
            control_vals = source.field_values[fld_name][sl]
            self.assertEqual(control_vals, test_vals)

    def test03c_layer_references(self):
        """
        Ensure OGR objects keep references to the objects they belong to.
        """
        source = ds_list[0]

        # See ticket #9448.
        def get_layer():
            # This DataSource object is not accessible outside this
            # scope.  However, a reference should still be kept alive
            # on the `Layer` returned.
            ds = DataSource(source.ds)
            return ds[0]

        # Making sure we can call OGR routines on the Layer returned.
        lyr = get_layer()
        self.assertEqual(source.nfeat, len(lyr))
        self.assertEqual(source.gtype, lyr.geom_type.num)

        # Same issue for Feature/Field objects, see #18640
        self.assertEqual(str(lyr[0]['str']), "1")

    def test04_features(self):
        "Testing Data Source Features."
        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer
            for layer in ds:
                # Incrementing through each feature in the layer
                for feat in layer:
                    # Making sure the number of fields, and the geometry type
                    # are what's expected.
                    self.assertEqual(source.nfld, len(list(feat)))
                    self.assertEqual(source.gtype, feat.geom_type)

                    # Making sure the fields match to an appropriate OFT type.
                    for k, v in source.fields.items():
                        # Making sure we get the proper OGR Field instance, using
                        # a string value index for the feature.
                        self.assertEqual(True, isinstance(feat[k], v))

                    # Testing Feature.__iter__
                    for fld in feat:
                        self.assertEqual(True, fld.name in source.fields.keys())

    def test05_geometries(self):
        "Testing Geometries from Data Source Features."
        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer and feature.
            for layer in ds:
                for feat in layer:
                    g = feat.geom

                    # Making sure we get the right Geometry name & type
                    self.assertEqual(source.geom, g.geom_name)
                    self.assertEqual(source.gtype, g.geom_type)

                    # Making sure the SpatialReference is as expected.
                    if hasattr(source, 'srs_wkt'):
                        self.assertEqual(
                            source.srs_wkt,
                            # Depending on lib versions, WGS_84 might be WGS_1984
                            g.srs.wkt.replace('SPHEROID["WGS_84"', 'SPHEROID["WGS_1984"')
                        )

    def test06_spatial_filter(self):
        "Testing the Layer.spatial_filter property."
        ds = DataSource(get_ds_file('cities', 'shp'))
        lyr = ds[0]

        # When not set, it should be None.
        self.assertEqual(None, lyr.spatial_filter)

        # Must be set a/an OGRGeometry or 4-tuple.
        self.assertRaises(TypeError, lyr._set_spatial_filter, 'foo')

        # Setting the spatial filter with a tuple/list with the extent of
        # a buffer centering around Pueblo.
        self.assertRaises(ValueError, lyr._set_spatial_filter, list(range(5)))
        filter_extent = (-105.609252, 37.255001, -103.609252, 39.255001)
        lyr.spatial_filter = (-105.609252, 37.255001, -103.609252, 39.255001)
        self.assertEqual(OGRGeometry.from_bbox(filter_extent), lyr.spatial_filter)
        feats = [feat for feat in lyr]
        self.assertEqual(1, len(feats))
        self.assertEqual('Pueblo', feats[0].get('Name'))

        # Setting the spatial filter with an OGRGeometry for buffer centering
        # around Houston.
        filter_geom = OGRGeometry('POLYGON((-96.363151 28.763374,-94.363151 28.763374,-94.363151 30.763374,-96.363151 30.763374,-96.363151 28.763374))')
        lyr.spatial_filter = filter_geom
        self.assertEqual(filter_geom, lyr.spatial_filter)
        feats = [feat for feat in lyr]
        self.assertEqual(1, len(feats))
        self.assertEqual('Houston', feats[0].get('Name'))

        # Clearing the spatial filter by setting it to None.  Now
        # should indicate that there are 3 features in the Layer.
        lyr.spatial_filter = None
        self.assertEqual(3, len(lyr))

    def test07_integer_overflow(self):
        "Testing that OFTReal fields, treated as OFTInteger, do not overflow."
        # Using *.dbf from Census 2010 TIGER Shapefile for Texas,
        # which has land area ('ALAND10') stored in a Real field
        # with no precision.
        ds = DataSource(os.path.join(TEST_DATA, 'texas.dbf'))
        feat = ds[0][0]
        # Reference value obtained using `ogrinfo`.
        self.assertEqual(676586997978, feat.get('ALAND10'))
