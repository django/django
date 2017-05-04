import os
import unittest
from copy import copy
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils.layermapping import (
    InvalidDecimal, InvalidString, LayerMapError, LayerMapping,
    MissingForeignKey,
)
from django.db import connection
from django.test import TestCase, override_settings

from .models import (
    City, County, CountyFeat, ICity1, ICity2, Interstate, Invalid, State,
    city_mapping, co_mapping, cofeat_mapping, inter_mapping,
)

shp_path = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, 'data'))
city_shp = os.path.join(shp_path, 'cities', 'cities.shp')
co_shp = os.path.join(shp_path, 'counties', 'counties.shp')
inter_shp = os.path.join(shp_path, 'interstates', 'interstates.shp')
invalid_shp = os.path.join(shp_path, 'invalid', 'emptypoints.shp')

# Dictionaries to hold what's expected in the county shapefile.
NAMES = ['Bexar', 'Galveston', 'Harris', 'Honolulu', 'Pueblo']
NUMS = [1, 2, 1, 19, 1]  # Number of polygons for each.
STATES = ['Texas', 'Texas', 'Texas', 'Hawaii', 'Colorado']


class LayerMapTest(TestCase):

    def test_init(self):
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
            with self.assertRaises(LayerMapError):
                LayerMapping(City, city_shp, bad_map)

        # A LookupError should be thrown for bogus encodings.
        with self.assertRaises(LookupError):
            LayerMapping(City, city_shp, city_mapping, encoding='foobar')

    def test_simple_layermap(self):
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
            self.assertEqual(feat['Created'].value, city.dt)

            # Comparing the geometries.
            pnt1, pnt2 = feat.geom, city.point
            self.assertAlmostEqual(pnt1.x, pnt2.x, 5)
            self.assertAlmostEqual(pnt1.y, pnt2.y, 5)

    def test_layermap_strict(self):
        "Testing the `strict` keyword, and import of a LineString shapefile."
        # When the `strict` keyword is set an error encountered will force
        # the importation to stop.
        with self.assertRaises(InvalidDecimal):
            lm = LayerMapping(Interstate, inter_shp, inter_mapping)
            lm.save(silent=True, strict=True)
        Interstate.objects.all().delete()

        # This LayerMapping should work b/c `strict` is not set.
        lm = LayerMapping(Interstate, inter_shp, inter_mapping)
        lm.save(silent=True)

        # Two interstate should have imported correctly.
        self.assertEqual(2, Interstate.objects.count())

        # Verifying the values in the layer w/the model.
        ds = DataSource(inter_shp)

        # Only the first two features of this shapefile are valid.
        valid_feats = ds[0][:2]
        for feat in valid_feats:
            istate = Interstate.objects.get(name=feat['Name'].value)

            if feat.fid == 0:
                self.assertEqual(Decimal(str(feat['Length'])), istate.length)
            elif feat.fid == 1:
                # Everything but the first two decimal digits were truncated,
                # because the Interstate model's `length` field has decimal_places=2.
                self.assertAlmostEqual(feat.get('Length'), float(istate.length), 2)

            for p1, p2 in zip(feat.geom, istate.path):
                self.assertAlmostEqual(p1[0], p2[0], 6)
                self.assertAlmostEqual(p1[1], p2[1], 6)

    def county_helper(self, county_feat=True):
        "Helper function for ensuring the integrity of the mapped County models."
        for name, n, st in zip(NAMES, NUMS, STATES):
            # Should only be one record b/c of `unique` keyword.
            c = County.objects.get(name=name)
            self.assertEqual(n, len(c.mpoly))
            self.assertEqual(st, c.state.name)  # Checking ForeignKey mapping.

            # Multiple records because `unique` was not set.
            if county_feat:
                qs = CountyFeat.objects.filter(name=name)
                self.assertEqual(n, qs.count())

    def test_layermap_unique_multigeometry_fk(self):
        "Testing the `unique`, and `transform`, geometry collection conversion, and ForeignKey mappings."
        # All the following should work.

        # Telling LayerMapping that we want no transformations performed on the data.
        lm = LayerMapping(County, co_shp, co_mapping, transform=False)

        # Specifying the source spatial reference system via the `source_srs` keyword.
        lm = LayerMapping(County, co_shp, co_mapping, source_srs=4269)
        lm = LayerMapping(County, co_shp, co_mapping, source_srs='NAD83')

        # Unique may take tuple or string parameters.
        for arg in ('name', ('name', 'mpoly')):
            lm = LayerMapping(County, co_shp, co_mapping, transform=False, unique=arg)

        # Now test for failures

        # Testing invalid params for the `unique` keyword.
        for e, arg in ((TypeError, 5.0), (ValueError, 'foobar'), (ValueError, ('name', 'mpolygon'))):
            with self.assertRaises(e):
                LayerMapping(County, co_shp, co_mapping, transform=False, unique=arg)

        # No source reference system defined in the shapefile, should raise an error.
        if connection.features.supports_transform:
            with self.assertRaises(LayerMapError):
                LayerMapping(County, co_shp, co_mapping)

        # Passing in invalid ForeignKey mapping parameters -- must be a dictionary
        # mapping for the model the ForeignKey points to.
        bad_fk_map1 = copy(co_mapping)
        bad_fk_map1['state'] = 'name'
        bad_fk_map2 = copy(co_mapping)
        bad_fk_map2['state'] = {'nombre': 'State'}
        with self.assertRaises(TypeError):
            LayerMapping(County, co_shp, bad_fk_map1, transform=False)
        with self.assertRaises(LayerMapError):
            LayerMapping(County, co_shp, bad_fk_map2, transform=False)

        # There exist no State models for the ForeignKey mapping to work -- should raise
        # a MissingForeignKey exception (this error would be ignored if the `strict`
        # keyword is not set).
        lm = LayerMapping(County, co_shp, co_mapping, transform=False, unique='name')
        with self.assertRaises(MissingForeignKey):
            lm.save(silent=True, strict=True)

        # Now creating the state models so the ForeignKey mapping may work.
        State.objects.bulk_create([
            State(name='Colorado'), State(name='Hawaii'), State(name='Texas')
        ])

        # If a mapping is specified as a collection, all OGR fields that
        # are not collections will be converted into them.  For example,
        # a Point column would be converted to MultiPoint. Other things being done
        # w/the keyword args:
        #  `transform=False`: Specifies that no transform is to be done; this
        #    has the effect of ignoring the spatial reference check (because the
        #    county shapefile does not have implicit spatial reference info).
        #
        #  `unique='name'`: Creates models on the condition that they have
        #    unique county names; geometries from each feature however will be
        #    appended to the geometry collection of the unique model.  Thus,
        #    all of the various islands in Honolulu county will be in in one
        #    database record with a MULTIPOLYGON type.
        lm = LayerMapping(County, co_shp, co_mapping, transform=False, unique='name')
        lm.save(silent=True, strict=True)

        # A reference that doesn't use the unique keyword; a new database record will
        # created for each polygon.
        lm = LayerMapping(CountyFeat, co_shp, cofeat_mapping, transform=False)
        lm.save(silent=True, strict=True)

        # The county helper is called to ensure integrity of County models.
        self.county_helper()

    def test_test_fid_range_step(self):
        "Tests the `fid_range` keyword and the `step` keyword of .save()."
        # Function for clearing out all the counties before testing.
        def clear_counties():
            County.objects.all().delete()

        State.objects.bulk_create([
            State(name='Colorado'), State(name='Hawaii'), State(name='Texas')
        ])

        # Initializing the LayerMapping object to use in these tests.
        lm = LayerMapping(County, co_shp, co_mapping, transform=False, unique='name')

        # Bad feature id ranges should raise a type error.
        bad_ranges = (5.0, 'foo', co_shp)
        for bad in bad_ranges:
            with self.assertRaises(TypeError):
                lm.save(fid_range=bad)

        # Step keyword should not be allowed w/`fid_range`.
        fr = (3, 5)  # layer[3:5]
        with self.assertRaises(LayerMapError):
            lm.save(fid_range=fr, step=10)
        lm.save(fid_range=fr)

        # Features IDs 3 & 4 are for Galveston County, Texas -- only
        # one model is returned because the `unique` keyword was set.
        qs = County.objects.all()
        self.assertEqual(1, qs.count())
        self.assertEqual('Galveston', qs[0].name)

        # Features IDs 5 and beyond for Honolulu County, Hawaii, and
        # FID 0 is for Pueblo County, Colorado.
        clear_counties()
        lm.save(fid_range=slice(5, None), silent=True, strict=True)  # layer[5:]
        lm.save(fid_range=slice(None, 1), silent=True, strict=True)  # layer[:1]

        # Only Pueblo & Honolulu counties should be present because of
        # the `unique` keyword.  Have to set `order_by` on this QuerySet
        # or else MySQL will return a different ordering than the other dbs.
        qs = County.objects.order_by('name')
        self.assertEqual(2, qs.count())
        hi, co = tuple(qs)
        hi_idx, co_idx = tuple(map(NAMES.index, ('Honolulu', 'Pueblo')))
        self.assertEqual('Pueblo', co.name)
        self.assertEqual(NUMS[co_idx], len(co.mpoly))
        self.assertEqual('Honolulu', hi.name)
        self.assertEqual(NUMS[hi_idx], len(hi.mpoly))

        # Testing the `step` keyword -- should get the same counties
        # regardless of we use a step that divides equally, that is odd,
        # or that is larger than the dataset.
        for st in (4, 7, 1000):
            clear_counties()
            lm.save(step=st, strict=True)
            self.county_helper(county_feat=False)

    def test_model_inheritance(self):
        "Tests LayerMapping on inherited models.  See #12093."
        icity_mapping = {'name': 'Name',
                         'population': 'Population',
                         'density': 'Density',
                         'point': 'POINT',
                         'dt': 'Created',
                         }

        # Parent model has geometry field.
        lm1 = LayerMapping(ICity1, city_shp, icity_mapping)
        lm1.save()

        # Grandparent has geometry field.
        lm2 = LayerMapping(ICity2, city_shp, icity_mapping)
        lm2.save()

        self.assertEqual(6, ICity1.objects.count())
        self.assertEqual(3, ICity2.objects.count())

    def test_invalid_layer(self):
        "Tests LayerMapping on invalid geometries.  See #15378."
        invalid_mapping = {'point': 'POINT'}
        lm = LayerMapping(Invalid, invalid_shp, invalid_mapping,
                          source_srs=4326)
        lm.save(silent=True)

    def test_charfield_too_short(self):
        mapping = copy(city_mapping)
        mapping['name_short'] = 'Name'
        lm = LayerMapping(City, city_shp, mapping)
        with self.assertRaises(InvalidString):
            lm.save(silent=True, strict=True)

    def test_textfield(self):
        "String content fits also in a TextField"
        mapping = copy(city_mapping)
        mapping['name_txt'] = 'Name'
        lm = LayerMapping(City, city_shp, mapping)
        lm.save(silent=True, strict=True)
        self.assertEqual(City.objects.count(), 3)
        self.assertEqual(City.objects.get(name='Houston').name_txt, "Houston")

    def test_encoded_name(self):
        """ Test a layer containing utf-8-encoded name """
        city_shp = os.path.join(shp_path, 'ch-city', 'ch-city.shp')
        lm = LayerMapping(City, city_shp, city_mapping)
        lm.save(silent=True, strict=True)
        self.assertEqual(City.objects.count(), 1)
        self.assertEqual(City.objects.all()[0].name, "Zürich")


class OtherRouter:
    def db_for_read(self, model, **hints):
        return 'other'

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, **hints):
        return True


@override_settings(DATABASE_ROUTERS=[OtherRouter()])
class LayerMapRouterTest(TestCase):
    multi_db = True

    @unittest.skipUnless(len(settings.DATABASES) > 1, 'multiple databases required')
    def test_layermapping_default_db(self):
        lm = LayerMapping(City, city_shp, city_mapping)
        self.assertEqual(lm.using, 'other')
