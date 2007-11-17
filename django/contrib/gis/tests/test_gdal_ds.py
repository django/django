import os, os.path, unittest
from django.contrib.gis.gdal import DataSource, Envelope, OGRException, OGRIndexError
from django.contrib.gis.gdal.field import OFTReal, OFTInteger, OFTString

# Path for SHP files
shp_path = os.path.dirname(__file__)
def get_shp(name):
    return shp_path + os.sep + name + os.sep + name + '.shp'

# Test SHP data source object
class TestSHP:
    def __init__(self, shp, **kwargs):
        self.ds = get_shp(shp)
        for key, value in kwargs.items():
            setattr(self, key, value)

# List of acceptable data sources.
ds_list = (TestSHP('test_point', nfeat=5, nfld=3, geom='POINT', gtype=1, fields={'dbl' : OFTReal, 'int' : OFTInteger, 'str' : OFTString,},
                   extent=(-1.35011,0.166623,-0.524093,0.824508), # Got extent from QGIS
                   srs_wkt='GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'),
           TestSHP('test_poly', nfeat=3, nfld=3, geom='POLYGON', gtype=3, fields={'float' : OFTReal, 'int' : OFTInteger, 'str' : OFTString,},
                   extent=(-1.01513,-0.558245,0.161876,0.839637), # Got extent from QGIS
                   srs_wkt='GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'),
           )

bad_ds = (TestSHP('foo'),
          )

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
            self.assertEqual('ESRI Shapefile', str(ds.driver))

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

    def test03_layers(self):
        "Testing Data Source Layers."

        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer, this tests __iter__
            for layer in ds:                
                # Making sure we get the number of features we expect
                self.assertEqual(len(layer), source.nfeat)

                layer[0] #can index
                layer[:1] #can slice

                # Making sure we get the number of fields we expect
                self.assertEqual(source.nfld, layer.num_fields)
                self.assertEqual(source.nfld, len(layer.fields))

                # Testing the layer's extent (an Envelope), and it's properties
                self.assertEqual(True, isinstance(layer.extent, Envelope))
                self.assertAlmostEqual(source.extent[0], layer.extent.min_x, 5)
                self.assertAlmostEqual(source.extent[1], layer.extent.min_y, 5)
                self.assertAlmostEqual(source.extent[2], layer.extent.max_x, 5)
                self.assertAlmostEqual(source.extent[3], layer.extent.max_y, 5)

                # Now checking the field names.
                flds = layer.fields
                for f in flds: self.assertEqual(True, f in source.fields)

    def test04_features(self):
        "Testing Data Source Features."
        for source in ds_list:
            ds = DataSource(source.ds)

            # Incrementing through each layer
            for layer in ds:
                # Incrementing through each feature in the layer
                for feat in layer:
                    # Making sure the number of fields is what's expected.
                    self.assertEqual(source.nfld, len(list(feat)))
                    self.assertEqual(source.gtype, feat.geom_type)

                    # Making sure the fields match to an appropriate OFT type.
                    for k, v in source.fields.items():
                        # Making sure we get the proper OGR Field instance, using
                        # a string value index for the feature.
                        self.assertEqual(True, isinstance(feat[k], v))

                    # Testing __iter__ on the Feature
                    for fld in feat: self.assertEqual(True, fld.name in source.fields.keys())
                        
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
                    self.assertEqual(source.srs_wkt, g.srs.wkt)
                        
def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(DataSourceTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
