import os, unittest
from copy import copy
from datetime import date
from decimal import Decimal
from models import City, Interstate, city_mapping, inter_mapping
from django.contrib.gis.utils.layermapping import LayerMapping, LayerMapError, InvalidDecimal
from django.contrib.gis.gdal import DataSource

shp_path = os.path.dirname(__file__)
city_shp = os.path.join(shp_path, 'cities/cities.shp')
inter_shp = os.path.join(shp_path, 'interstates/interstates.shp')

class LayerMapTest(unittest.TestCase):

    def test01_init(self):
        "Testing LayerMapping initialization."

        # Model field that does not exist.
        bad1 = copy(city_mapping)
        bad1['foobar'] = 'FooField'

        # Shapefile field that does not exist.
        bad2 = copy(city_mapping)
        bad2['name'] = 'Nombre'

        # Nonexistent geographic field type.
        bad3 = copy(city_mapping)
        bad3['point'] = 'CURVE'

        # Incrementing through the bad mapping dictionaries and
        # ensuring that a LayerMapError is raised.
        for bad_map in (bad1, bad2, bad3):
            try:
                lm = LayerMapping(City, city_shp, bad_map)
            except LayerMapError:
                pass
            else:
                self.fail('Expected a LayerMapError.')

        # A LookupError should be thrown for bogus encodings.
        try:
            lm = LayerMapping(City, city_shp, city_mapping, encoding='foobar')
        except LookupError:
            pass
        else:
            self.fail('Expected a LookupError')

    def test02_simple_layermap(self):
        "Test LayerMapping import of a simple point shapefile."

        # Setting up for the LayerMapping.
        lm = LayerMapping(City, city_shp, city_mapping)
        lm.save()

        # There should be three cities in the shape file.
        self.assertEqual(3, City.objects.count())

        # Opening up the shapefile, and verifying the values in each
        # of the features made it to the model.
        ds = DataSource(city_shp)
        layer = ds[0]
        for feat in layer:
            city = City.objects.get(name=feat['Name'].value)
            self.assertEqual(feat['Population'].value, city.population)
            self.assertEqual(Decimal(str(feat['Density'])), city.density)
            self.assertEqual(feat['Created'].value, city.date)

            # Comparing the geometries.
            pnt1, pnt2 = feat.geom, city.point
            self.assertAlmostEqual(pnt1.x, pnt2.x, 6)
            self.assertAlmostEqual(pnt1.y, pnt2.y, 6)

    def test03_layermap_strict(self):
        "Testing the `strict` keyword, and import of a LineString shapefile."

        # When the `strict` keyword is set an error encountered will force
        # the importation to stop.
        try:
            lm = LayerMapping(Interstate, inter_shp, inter_mapping, 
                              strict=True, silent=True)
            lm.save()
        except InvalidDecimal:
            pass
        else:
            self.fail('Should have failed on strict import with invalid decimal values.')

        # This LayerMapping should work b/c `strict` is not set.
        lm = LayerMapping(Interstate, inter_shp, inter_mapping, silent=True)
        lm.save()

        # Only one interstate should have imported correctly.
        self.assertEqual(1, Interstate.objects.count())
        
        # Verifying the values in the single feature w/the model.
        ds = DataSource(inter_shp)
        feat = ds[0][0]
        istate = Interstate.objects.get(name=feat['Name'].value)
        self.assertEqual(Decimal(str(feat['Length'])), istate.length)
        for p1, p2 in zip(feat.geom, istate.path):
            self.assertAlmostEqual(p1[0], p2[0], 6)
            self.assertAlmostEqual(p1[1], p2[1], 6)

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(LayerMapTest))
    return s
