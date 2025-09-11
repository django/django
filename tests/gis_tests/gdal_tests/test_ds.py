import os
import re
from datetime import datetime
from pathlib import Path

from django.contrib.gis.gdal import DataSource, Envelope, GDALException, OGRGeometry
from django.contrib.gis.gdal.field import OFTDateTime, OFTInteger, OFTReal, OFTString
from django.contrib.gis.geos import GEOSGeometry
from django.test import SimpleTestCase

from ..test_data import TEST_DATA, TestDS, get_ds_file

wgs_84_wkt = (
    'GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",SPHEROID["WGS_1984",'
    '6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",'
    "0.017453292519943295]]"
)
# Using a regex because of small differences depending on GDAL versions.
wgs_84_wkt_regex = r'^GEOGCS\["(GCS_)?WGS[ _](19)?84".*$'

datetime_format = "%Y-%m-%dT%H:%M:%S"

# List of acceptable data sources.
ds_list = (
    TestDS(
        "test_point",
        nfeat=5,
        nfld=3,
        geom="POINT",
        gtype=1,
        driver="ESRI Shapefile",
        fields={"dbl": OFTReal, "int": OFTInteger, "str": OFTString},
        extent=(-1.35011, 0.166623, -0.524093, 0.824508),  # Got extent from QGIS
        srs_wkt=wgs_84_wkt,
        field_values={
            "dbl": [float(i) for i in range(1, 6)],
            "int": list(range(1, 6)),
            "str": [str(i) for i in range(1, 6)],
        },
        fids=range(5),
    ),
    TestDS(
        "test_vrt",
        ext="vrt",
        nfeat=3,
        nfld=3,
        geom="POINT",
        gtype="Point25D",
        driver="OGR_VRT",
        fields={
            "POINT_X": OFTString,
            "POINT_Y": OFTString,
            "NUM": OFTString,
        },  # VRT uses CSV, which all types are OFTString.
        extent=(1.0, 2.0, 100.0, 523.5),  # Min/Max from CSV
        field_values={
            "POINT_X": ["1.0", "5.0", "100.0"],
            "POINT_Y": ["2.0", "23.0", "523.5"],
            "NUM": ["5", "17", "23"],
        },
        fids=range(1, 4),
    ),
    TestDS(
        "test_poly",
        nfeat=3,
        nfld=3,
        geom="POLYGON",
        gtype=3,
        driver="ESRI Shapefile",
        fields={"float": OFTReal, "int": OFTInteger, "str": OFTString},
        extent=(-1.01513, -0.558245, 0.161876, 0.839637),  # Got extent from QGIS
        srs_wkt=wgs_84_wkt,
    ),
    TestDS(
        "has_nulls",
        nfeat=3,
        nfld=6,
        geom="POLYGON",
        gtype=3,
        driver="GeoJSON",
        ext="geojson",
        fields={
            "uuid": OFTString,
            "name": OFTString,
            "num": OFTReal,
            "integer": OFTInteger,
            "datetime": OFTDateTime,
            "boolean": OFTInteger,
        },
        extent=(-75.274200, 39.846504, -74.959717, 40.119040),  # Got extent from QGIS
        field_values={
            "uuid": [
                "1378c26f-cbe6-44b0-929f-eb330d4991f5",
                "fa2ba67c-a135-4338-b924-a9622b5d869f",
                "4494c1f3-55ab-4256-b365-12115cb388d5",
            ],
            "name": ["Philadelphia", None, "north"],
            "num": [1.001, None, 0.0],
            "integer": [5, None, 8],
            "boolean": [True, None, False],
            "datetime": [
                datetime.strptime("1994-08-14T11:32:14", datetime_format),
                None,
                datetime.strptime("2018-11-29T03:02:52", datetime_format),
            ],
        },
        fids=range(3),
    ),
)

bad_ds = (TestDS("foo"),)


class DataSourceTest(SimpleTestCase):
    def test01_valid_shp(self):
        "Testing valid SHP Data Source files."

        for source in ds_list:
            # Loading up the data source
            ds = DataSource(source.ds)

            # The layer count is what's expected (only 1 layer in a SHP file).
            self.assertEqual(1, len(ds))

            # Making sure GetName works
            self.assertEqual(source.ds, ds.name)

            # Making sure the driver name matches up
            self.assertEqual(source.driver, str(ds.driver))

            # Making sure indexing works
            msg = "Index out of range when accessing layers in a datasource: %s."
            with self.assertRaisesMessage(IndexError, msg % len(ds)):
                ds.__getitem__(len(ds))

            with self.assertRaisesMessage(
                IndexError, "Invalid OGR layer name given: invalid."
            ):
                ds.__getitem__("invalid")

    def test_ds_input_pathlib(self):
        test_shp = Path(get_ds_file("test_point", "shp"))
        ds = DataSource(test_shp)
        self.assertEqual(len(ds), 1)

    def test02_invalid_shp(self):
        "Testing invalid SHP files for the Data Source."
        for source in bad_ds:
            with self.assertRaises(GDALException):
                DataSource(source.ds)

    def test03a_layers(self):
        "Testing Data Source Layers."
        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer, this tests DataSource.__iter__
            for layer in ds:
                self.assertEqual(layer.name, source.name)
                self.assertEqual(str(layer), source.name)
                # Making sure we get the number of features we expect
                self.assertEqual(len(layer), source.nfeat)

                # Making sure we get the number of fields we expect
                self.assertEqual(source.nfld, layer.num_fields)
                self.assertEqual(source.nfld, len(layer.fields))

                # Testing the layer's extent (an Envelope), and its properties
                self.assertIsInstance(layer.extent, Envelope)
                self.assertAlmostEqual(source.extent[0], layer.extent.min_x, 5)
                self.assertAlmostEqual(source.extent[1], layer.extent.min_y, 5)
                self.assertAlmostEqual(source.extent[2], layer.extent.max_x, 5)
                self.assertAlmostEqual(source.extent[3], layer.extent.max_y, 5)

                # Now checking the field names.
                flds = layer.fields
                for f in flds:
                    self.assertIn(f, source.fields)

                # Negative FIDs are not allowed.
                with self.assertRaisesMessage(
                    IndexError, "Negative indices are not allowed on OGR Layers."
                ):
                    layer.__getitem__(-1)
                with self.assertRaisesMessage(IndexError, "Invalid feature id: 50000."):
                    layer.__getitem__(50000)

                if hasattr(source, "field_values"):
                    # Testing `Layer.get_fields` (which uses Layer.__iter__)
                    for fld_name, fld_value in source.field_values.items():
                        self.assertEqual(fld_value, layer.get_fields(fld_name))

                    # Testing `Layer.__getitem__`.
                    for i, fid in enumerate(source.fids):
                        feat = layer[fid]
                        self.assertEqual(fid, feat.fid)
                        # Maybe this should be in the test below, but we might
                        # as well test the feature values here while in this
                        # loop.
                        for fld_name, fld_value in source.field_values.items():
                            self.assertEqual(fld_value[i], feat.get(fld_name))

                        msg = (
                            "Index out of range when accessing field in a feature: %s."
                        )
                        with self.assertRaisesMessage(IndexError, msg % len(feat)):
                            feat.__getitem__(len(feat))

                        with self.assertRaisesMessage(
                            IndexError, "Invalid OFT field name given: invalid."
                        ):
                            feat.__getitem__("invalid")

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
            # scope. However, a reference should still be kept alive
            # on the `Layer` returned.
            ds = DataSource(source.ds)
            return ds[0]

        # Making sure we can call OGR routines on the Layer returned.
        lyr = get_layer()
        self.assertEqual(source.nfeat, len(lyr))
        self.assertEqual(source.gtype, lyr.geom_type.num)

        # Same issue for Feature/Field objects, see #18640
        self.assertEqual(str(lyr[0]["str"]), "1")

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
                        # Making sure we get the proper OGR Field instance,
                        # using a string value index for the feature.
                        self.assertIsInstance(feat[k], v)
                    self.assertIsInstance(feat.fields[0], str)

                    # Testing Feature.__iter__
                    for fld in feat:
                        self.assertIn(fld.name, source.fields)

    def test05_geometries(self):
        "Testing Geometries from Data Source Features."
        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer and feature.
            for layer in ds:
                geoms = layer.get_geoms()
                geos_geoms = layer.get_geoms(geos=True)
                self.assertEqual(len(geoms), len(geos_geoms))
                self.assertEqual(len(geoms), len(layer))
                for feat, geom, geos_geom in zip(layer, geoms, geos_geoms):
                    g = feat.geom
                    self.assertEqual(geom, g)
                    self.assertIsInstance(geos_geom, GEOSGeometry)
                    self.assertEqual(g, geos_geom.ogr)
                    # Making sure we get the right Geometry name & type
                    self.assertEqual(source.geom, g.geom_name)
                    self.assertEqual(source.gtype, g.geom_type)

                    # Making sure the SpatialReference is as expected.
                    if hasattr(source, "srs_wkt"):
                        self.assertIsNotNone(re.match(wgs_84_wkt_regex, g.srs.wkt))

    def test06_spatial_filter(self):
        "Testing the Layer.spatial_filter property."
        ds = DataSource(get_ds_file("cities", "shp"))
        lyr = ds[0]

        # When not set, it should be None.
        self.assertIsNone(lyr.spatial_filter)

        # Must be set a/an OGRGeometry or 4-tuple.
        with self.assertRaises(TypeError):
            lyr._set_spatial_filter("foo")

        # Setting the spatial filter with a tuple/list with the extent of
        # a buffer centering around Pueblo.
        with self.assertRaises(ValueError):
            lyr._set_spatial_filter(list(range(5)))
        filter_extent = (-105.609252, 37.255001, -103.609252, 39.255001)
        lyr.spatial_filter = (-105.609252, 37.255001, -103.609252, 39.255001)
        self.assertEqual(OGRGeometry.from_bbox(filter_extent), lyr.spatial_filter)
        feats = [feat for feat in lyr]
        self.assertEqual(1, len(feats))
        self.assertEqual("Pueblo", feats[0].get("Name"))

        # Setting the spatial filter with an OGRGeometry for buffer centering
        # around Houston.
        filter_geom = OGRGeometry(
            "POLYGON((-96.363151 28.763374,-94.363151 28.763374,"
            "-94.363151 30.763374,-96.363151 30.763374,-96.363151 28.763374))"
        )
        lyr.spatial_filter = filter_geom
        self.assertEqual(filter_geom, lyr.spatial_filter)
        feats = [feat for feat in lyr]
        self.assertEqual(1, len(feats))
        self.assertEqual("Houston", feats[0].get("Name"))

        # Clearing the spatial filter by setting it to None. Now
        # should indicate that there are 3 features in the Layer.
        lyr.spatial_filter = None
        self.assertEqual(3, len(lyr))

    def test07_integer_overflow(self):
        "Testing that OFTReal fields, treated as OFTInteger, do not overflow."
        # Using *.dbf from Census 2010 TIGER Shapefile for Texas,
        # which has land area ('ALAND10') stored in a Real field
        # with no precision.
        ds = DataSource(os.path.join(TEST_DATA, "texas.dbf"))
        feat = ds[0][0]
        # Reference value obtained using `ogrinfo`.
        self.assertEqual(676586997978, feat.get("ALAND10"))

    def test_nonexistent_field(self):
        source = ds_list[0]
        ds = DataSource(source.ds)
        msg = "invalid field name: nonexistent"
        with self.assertRaisesMessage(GDALException, msg):
            ds[0].get_fields("nonexistent")
