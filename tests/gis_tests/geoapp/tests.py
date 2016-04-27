from __future__ import unicode_literals

import re
import tempfile

from django.contrib.gis import gdal
from django.contrib.gis.db.models import Extent, MakeLine, Union
from django.contrib.gis.geos import (
    GeometryCollection, GEOSGeometry, LinearRing, LineString, Point, Polygon,
    fromstr,
)
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, ignore_warnings, skipUnlessDBFeature
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning

from ..utils import no_oracle, oracle, postgis, skipUnlessGISLookup, spatialite
from .models import (
    City, Country, Feature, MinusOneSRID, NonConcreteModel, PennsylvaniaCity,
    State, Track,
)


def postgis_bug_version():
    spatial_version = getattr(connection.ops, "spatial_version", (0, 0, 0))
    return spatial_version and (2, 0, 0) <= spatial_version <= (2, 0, 1)


@skipUnlessDBFeature("gis_enabled")
class GeoModelTest(TestCase):
    fixtures = ['initial']

    def test_fixtures(self):
        "Testing geographic model initialization from fixtures."
        # Ensuring that data was loaded from initial data fixtures.
        self.assertEqual(2, Country.objects.count())
        self.assertEqual(8, City.objects.count())
        self.assertEqual(2, State.objects.count())

    def test_proxy(self):
        "Testing Lazy-Geometry support (using the GeometryProxy)."
        # Testing on a Point
        pnt = Point(0, 0)
        nullcity = City(name='NullCity', point=pnt)
        nullcity.save()

        # Making sure TypeError is thrown when trying to set with an
        #  incompatible type.
        for bad in [5, 2.0, LineString((0, 0), (1, 1))]:
            try:
                nullcity.point = bad
            except TypeError:
                pass
            else:
                self.fail('Should throw a TypeError')

        # Now setting with a compatible GEOS Geometry, saving, and ensuring
        #  the save took, notice no SRID is explicitly set.
        new = Point(5, 23)
        nullcity.point = new

        # Ensuring that the SRID is automatically set to that of the
        #  field after assignment, but before saving.
        self.assertEqual(4326, nullcity.point.srid)
        nullcity.save()

        # Ensuring the point was saved correctly after saving
        self.assertEqual(new, City.objects.get(name='NullCity').point)

        # Setting the X and Y of the Point
        nullcity.point.x = 23
        nullcity.point.y = 5
        # Checking assignments pre & post-save.
        self.assertNotEqual(Point(23, 5), City.objects.get(name='NullCity').point)
        nullcity.save()
        self.assertEqual(Point(23, 5), City.objects.get(name='NullCity').point)
        nullcity.delete()

        # Testing on a Polygon
        shell = LinearRing((0, 0), (0, 100), (100, 100), (100, 0), (0, 0))
        inner = LinearRing((40, 40), (40, 60), (60, 60), (60, 40), (40, 40))

        # Creating a State object using a built Polygon
        ply = Polygon(shell, inner)
        nullstate = State(name='NullState', poly=ply)
        self.assertEqual(4326, nullstate.poly.srid)  # SRID auto-set from None
        nullstate.save()

        ns = State.objects.get(name='NullState')
        self.assertEqual(ply, ns.poly)

        # Testing the `ogr` and `srs` lazy-geometry properties.
        if gdal.HAS_GDAL:
            self.assertIsInstance(ns.poly.ogr, gdal.OGRGeometry)
            self.assertEqual(ns.poly.wkb, ns.poly.ogr.wkb)
            self.assertIsInstance(ns.poly.srs, gdal.SpatialReference)
            self.assertEqual('WGS 84', ns.poly.srs.name)

        # Changing the interior ring on the poly attribute.
        new_inner = LinearRing((30, 30), (30, 70), (70, 70), (70, 30), (30, 30))
        ns.poly[1] = new_inner
        ply[1] = new_inner
        self.assertEqual(4326, ns.poly.srid)
        ns.save()
        self.assertEqual(ply, State.objects.get(name='NullState').poly)
        ns.delete()

    @skipUnlessDBFeature("supports_transform")
    def test_lookup_insert_transform(self):
        "Testing automatic transform for lookups and inserts."
        # San Antonio in 'WGS84' (SRID 4326)
        sa_4326 = 'POINT (-98.493183 29.424170)'
        wgs_pnt = fromstr(sa_4326, srid=4326)  # Our reference point in WGS84

        # Oracle doesn't have SRID 3084, using 41157.
        if oracle:
            # San Antonio in 'Texas 4205, Southern Zone (1983, meters)' (SRID 41157)
            # Used the following Oracle SQL to get this value:
            #  SELECT SDO_UTIL.TO_WKTGEOMETRY(
            #    SDO_CS.TRANSFORM(SDO_GEOMETRY('POINT (-98.493183 29.424170)', 4326), 41157))
            #  )
            #  FROM DUAL;
            nad_wkt = 'POINT (300662.034646583 5416427.45974934)'
            nad_srid = 41157
        else:
            # San Antonio in 'NAD83(HARN) / Texas Centric Lambert Conformal' (SRID 3084)
            # Used ogr.py in gdal 1.4.1 for this transform
            nad_wkt = 'POINT (1645978.362408288754523 6276356.025927528738976)'
            nad_srid = 3084

        # Constructing & querying with a point from a different SRID. Oracle
        # `SDO_OVERLAPBDYINTERSECT` operates differently from
        # `ST_Intersects`, so contains is used instead.
        nad_pnt = fromstr(nad_wkt, srid=nad_srid)
        if oracle:
            tx = Country.objects.get(mpoly__contains=nad_pnt)
        else:
            tx = Country.objects.get(mpoly__intersects=nad_pnt)
        self.assertEqual('Texas', tx.name)

        # Creating San Antonio.  Remember the Alamo.
        sa = City.objects.create(name='San Antonio', point=nad_pnt)

        # Now verifying that San Antonio was transformed correctly
        sa = City.objects.get(name='San Antonio')
        self.assertAlmostEqual(wgs_pnt.x, sa.point.x, 6)
        self.assertAlmostEqual(wgs_pnt.y, sa.point.y, 6)

        # If the GeometryField SRID is -1, then we shouldn't perform any
        # transformation if the SRID of the input geometry is different.
        m1 = MinusOneSRID(geom=Point(17, 23, srid=4326))
        m1.save()
        self.assertEqual(-1, m1.geom.srid)

    def test_createnull(self):
        "Testing creating a model instance and the geometry being None"
        c = City()
        self.assertEqual(c.point, None)

    def test_geometryfield(self):
        "Testing the general GeometryField."
        Feature(name='Point', geom=Point(1, 1)).save()
        Feature(name='LineString', geom=LineString((0, 0), (1, 1), (5, 5))).save()
        Feature(name='Polygon', geom=Polygon(LinearRing((0, 0), (0, 5), (5, 5), (5, 0), (0, 0)))).save()
        Feature(name='GeometryCollection',
                geom=GeometryCollection(Point(2, 2), LineString((0, 0), (2, 2)),
                                        Polygon(LinearRing((0, 0), (0, 5), (5, 5), (5, 0), (0, 0))))).save()

        f_1 = Feature.objects.get(name='Point')
        self.assertIsInstance(f_1.geom, Point)
        self.assertEqual((1.0, 1.0), f_1.geom.tuple)
        f_2 = Feature.objects.get(name='LineString')
        self.assertIsInstance(f_2.geom, LineString)
        self.assertEqual(((0.0, 0.0), (1.0, 1.0), (5.0, 5.0)), f_2.geom.tuple)

        f_3 = Feature.objects.get(name='Polygon')
        self.assertIsInstance(f_3.geom, Polygon)
        f_4 = Feature.objects.get(name='GeometryCollection')
        self.assertIsInstance(f_4.geom, GeometryCollection)
        self.assertEqual(f_3.geom, f_4.geom[2])

    @skipUnlessDBFeature("supports_transform")
    def test_inherited_geofields(self):
        "Test GeoQuerySet methods on inherited Geometry fields."
        # Creating a Pennsylvanian city.
        PennsylvaniaCity.objects.create(name='Mansfield', county='Tioga', point='POINT(-77.071445 41.823881)')

        # All transformation SQL will need to be performed on the
        # _parent_ table.
        qs = PennsylvaniaCity.objects.transform(32128)

        self.assertEqual(1, qs.count())
        for pc in qs:
            self.assertEqual(32128, pc.point.srid)

    def test_raw_sql_query(self):
        "Testing raw SQL query."
        cities1 = City.objects.all()
        # Only PostGIS would support a 'select *' query because of its recognized
        # HEXEWKB format for geometry fields
        as_text = 'ST_AsText(%s)' if postgis else connection.ops.select
        cities2 = City.objects.raw(
            'select id, name, %s from geoapp_city' % as_text % 'point'
        )
        self.assertEqual(len(cities1), len(list(cities2)))
        self.assertIsInstance(cities2[0].point, Point)

    def test_dumpdata_loaddata_cycle(self):
        """
        Test a dumpdata/loaddata cycle with geographic data.
        """
        out = six.StringIO()
        original_data = list(City.objects.all().order_by('name'))
        call_command('dumpdata', 'geoapp.City', stdout=out)
        result = out.getvalue()
        houston = City.objects.get(name='Houston')
        self.assertIn('"point": "%s"' % houston.point.ewkt, result)

        # Reload now dumped data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as tmp:
            tmp.write(result)
            tmp.seek(0)
            call_command('loaddata', tmp.name, verbosity=0)
        self.assertListEqual(original_data, list(City.objects.all().order_by('name')))


@skipUnlessDBFeature("gis_enabled")
class GeoLookupTest(TestCase):
    fixtures = ['initial']

    def test_disjoint_lookup(self):
        "Testing the `disjoint` lookup type."
        ptown = City.objects.get(name='Pueblo')
        qs1 = City.objects.filter(point__disjoint=ptown.point)
        self.assertEqual(7, qs1.count())

        if connection.features.supports_real_shape_operations:
            qs2 = State.objects.filter(poly__disjoint=ptown.point)
            self.assertEqual(1, qs2.count())
            self.assertEqual('Kansas', qs2[0].name)

    def test_contains_contained_lookups(self):
        "Testing the 'contained', 'contains', and 'bbcontains' lookup types."
        # Getting Texas, yes we were a country -- once ;)
        texas = Country.objects.get(name='Texas')

        # Seeing what cities are in Texas, should get Houston and Dallas,
        #  and Oklahoma City because 'contained' only checks on the
        #  _bounding box_ of the Geometries.
        if connection.features.supports_contained_lookup:
            qs = City.objects.filter(point__contained=texas.mpoly)
            self.assertEqual(3, qs.count())
            cities = ['Houston', 'Dallas', 'Oklahoma City']
            for c in qs:
                self.assertIn(c.name, cities)

        # Pulling out some cities.
        houston = City.objects.get(name='Houston')
        wellington = City.objects.get(name='Wellington')
        pueblo = City.objects.get(name='Pueblo')
        okcity = City.objects.get(name='Oklahoma City')
        lawrence = City.objects.get(name='Lawrence')

        # Now testing contains on the countries using the points for
        #  Houston and Wellington.
        tx = Country.objects.get(mpoly__contains=houston.point)  # Query w/GEOSGeometry
        nz = Country.objects.get(mpoly__contains=wellington.point.hex)  # Query w/EWKBHEX
        self.assertEqual('Texas', tx.name)
        self.assertEqual('New Zealand', nz.name)

        # Testing `contains` on the states using the point for Lawrence.
        ks = State.objects.get(poly__contains=lawrence.point)
        self.assertEqual('Kansas', ks.name)

        # Pueblo and Oklahoma City (even though OK City is within the bounding box of Texas)
        # are not contained in Texas or New Zealand.
        self.assertEqual(len(Country.objects.filter(mpoly__contains=pueblo.point)), 0)  # Query w/GEOSGeometry object
        self.assertEqual(len(Country.objects.filter(mpoly__contains=okcity.point.wkt)),
                         0 if connection.features.supports_real_shape_operations else 1)  # Query w/WKT

        # OK City is contained w/in bounding box of Texas.
        if connection.features.supports_bbcontains_lookup:
            qs = Country.objects.filter(mpoly__bbcontains=okcity.point)
            self.assertEqual(1, len(qs))
            self.assertEqual('Texas', qs[0].name)

    @skipUnlessDBFeature("supports_crosses_lookup")
    def test_crosses_lookup(self):
        Track.objects.create(
            name='Line1',
            line=LineString([(-95, 29), (-60, 0)])
        )
        self.assertEqual(
            Track.objects.filter(line__crosses=LineString([(-95, 0), (-60, 29)])).count(),
            1
        )
        self.assertEqual(
            Track.objects.filter(line__crosses=LineString([(-95, 30), (0, 30)])).count(),
            0
        )

    @skipUnlessDBFeature("supports_isvalid_lookup")
    def test_isvalid_lookup(self):
        invalid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 1 1, 1 0, 0 0))')
        State.objects.create(name='invalid', poly=invalid_geom)
        self.assertEqual(State.objects.filter(poly__isvalid=False).count(), 1)
        self.assertEqual(State.objects.filter(poly__isvalid=True).count(), State.objects.count() - 1)

    @skipUnlessDBFeature("supports_left_right_lookups")
    def test_left_right_lookups(self):
        "Testing the 'left' and 'right' lookup types."
        # Left: A << B => true if xmax(A) < xmin(B)
        # Right: A >> B => true if xmin(A) > xmax(B)
        # See: BOX2D_left() and BOX2D_right() in lwgeom_box2dfloat4.c in PostGIS source.

        # The left/right lookup tests are known failures on PostGIS 2.0/2.0.1
        # http://trac.osgeo.org/postgis/ticket/2035
        if postgis_bug_version():
            self.skipTest("PostGIS 2.0/2.0.1 left and right lookups are known to be buggy.")

        # Getting the borders for Colorado & Kansas
        co_border = State.objects.get(name='Colorado').poly
        ks_border = State.objects.get(name='Kansas').poly

        # Note: Wellington has an 'X' value of 174, so it will not be considered
        # to the left of CO.

        # These cities should be strictly to the right of the CO border.
        cities = ['Houston', 'Dallas', 'Oklahoma City',
                  'Lawrence', 'Chicago', 'Wellington']
        qs = City.objects.filter(point__right=co_border)
        self.assertEqual(6, len(qs))
        for c in qs:
            self.assertIn(c.name, cities)

        # These cities should be strictly to the right of the KS border.
        cities = ['Chicago', 'Wellington']
        qs = City.objects.filter(point__right=ks_border)
        self.assertEqual(2, len(qs))
        for c in qs:
            self.assertIn(c.name, cities)

        # Note: Wellington has an 'X' value of 174, so it will not be considered
        #  to the left of CO.
        vic = City.objects.get(point__left=co_border)
        self.assertEqual('Victoria', vic.name)

        cities = ['Pueblo', 'Victoria']
        qs = City.objects.filter(point__left=ks_border)
        self.assertEqual(2, len(qs))
        for c in qs:
            self.assertIn(c.name, cities)

    @skipUnlessGISLookup("strictly_above", "strictly_below")
    def test_strictly_above_below_lookups(self):
        dallas = City.objects.get(name='Dallas')
        self.assertQuerysetEqual(
            City.objects.filter(point__strictly_above=dallas.point).order_by('name'),
            ['Chicago', 'Lawrence', 'Oklahoma City', 'Pueblo', 'Victoria'],
            lambda b: b.name
        )
        self.assertQuerysetEqual(
            City.objects.filter(point__strictly_below=dallas.point).order_by('name'),
            ['Houston', 'Wellington'],
            lambda b: b.name
        )

    def test_equals_lookups(self):
        "Testing the 'same_as' and 'equals' lookup types."
        pnt = fromstr('POINT (-95.363151 29.763374)', srid=4326)
        c1 = City.objects.get(point=pnt)
        c2 = City.objects.get(point__same_as=pnt)
        c3 = City.objects.get(point__equals=pnt)
        for c in [c1, c2, c3]:
            self.assertEqual('Houston', c.name)

    @skipUnlessDBFeature("supports_null_geometries")
    def test_null_geometries(self):
        "Testing NULL geometry support, and the `isnull` lookup type."
        # Creating a state with a NULL boundary.
        State.objects.create(name='Puerto Rico')

        # Querying for both NULL and Non-NULL values.
        nullqs = State.objects.filter(poly__isnull=True)
        validqs = State.objects.filter(poly__isnull=False)

        # Puerto Rico should be NULL (it's a commonwealth unincorporated territory)
        self.assertEqual(1, len(nullqs))
        self.assertEqual('Puerto Rico', nullqs[0].name)

        # The valid states should be Colorado & Kansas
        self.assertEqual(2, len(validqs))
        state_names = [s.name for s in validqs]
        self.assertIn('Colorado', state_names)
        self.assertIn('Kansas', state_names)

        # Saving another commonwealth w/a NULL geometry.
        nmi = State.objects.create(name='Northern Mariana Islands', poly=None)
        self.assertEqual(nmi.poly, None)

        # Assigning a geometry and saving -- then UPDATE back to NULL.
        nmi.poly = 'POLYGON((0 0,1 0,1 1,1 0,0 0))'
        nmi.save()
        State.objects.filter(name='Northern Mariana Islands').update(poly=None)
        self.assertIsNone(State.objects.get(name='Northern Mariana Islands').poly)

    @skipUnlessDBFeature("supports_relate_lookup")
    def test_relate_lookup(self):
        "Testing the 'relate' lookup type."
        # To make things more interesting, we will have our Texas reference point in
        # different SRIDs.
        pnt1 = fromstr('POINT (649287.0363174 4177429.4494686)', srid=2847)
        pnt2 = fromstr('POINT(-98.4919715741052 29.4333344025053)', srid=4326)

        # Not passing in a geometry as first param should
        # raise a type error when initializing the GeoQuerySet
        with self.assertRaises(ValueError):
            Country.objects.filter(mpoly__relate=(23, 'foo'))

        # Making sure the right exception is raised for the given
        # bad arguments.
        for bad_args, e in [((pnt1, 0), ValueError), ((pnt2, 'T*T***FF*', 0), ValueError)]:
            qs = Country.objects.filter(mpoly__relate=bad_args)
            with self.assertRaises(e):
                qs.count()

        # Relate works differently for the different backends.
        if postgis or spatialite:
            contains_mask = 'T*T***FF*'
            within_mask = 'T*F**F***'
            intersects_mask = 'T********'
        elif oracle:
            contains_mask = 'contains'
            within_mask = 'inside'
            # TODO: This is not quite the same as the PostGIS mask above
            intersects_mask = 'overlapbdyintersect'

        # Testing contains relation mask.
        self.assertEqual('Texas', Country.objects.get(mpoly__relate=(pnt1, contains_mask)).name)
        self.assertEqual('Texas', Country.objects.get(mpoly__relate=(pnt2, contains_mask)).name)

        # Testing within relation mask.
        ks = State.objects.get(name='Kansas')
        self.assertEqual('Lawrence', City.objects.get(point__relate=(ks.poly, within_mask)).name)

        # Testing intersection relation mask.
        if not oracle:
            self.assertEqual('Texas', Country.objects.get(mpoly__relate=(pnt1, intersects_mask)).name)
            self.assertEqual('Texas', Country.objects.get(mpoly__relate=(pnt2, intersects_mask)).name)
            self.assertEqual('Lawrence', City.objects.get(point__relate=(ks.poly, intersects_mask)).name)


@skipUnlessDBFeature("gis_enabled")
@ignore_warnings(category=RemovedInDjango20Warning)
class GeoQuerySetTest(TestCase):
    fixtures = ['initial']

    # Please keep the tests in GeoQuerySet method's alphabetic order

    @skipUnlessDBFeature("has_centroid_method")
    def test_centroid(self):
        "Testing the `centroid` GeoQuerySet method."
        qs = State.objects.exclude(poly__isnull=True).centroid()
        if oracle:
            tol = 0.1
        elif spatialite:
            tol = 0.000001
        else:
            tol = 0.000000001
        for s in qs:
            self.assertTrue(s.poly.centroid.equals_exact(s.centroid, tol))

    @skipUnlessDBFeature(
        "has_difference_method", "has_intersection_method",
        "has_sym_difference_method", "has_union_method")
    def test_diff_intersection_union(self):
        "Testing the `difference`, `intersection`, `sym_difference`, and `union` GeoQuerySet methods."
        geom = Point(5, 23)
        qs = Country.objects.all().difference(geom).sym_difference(geom).union(geom)

        # XXX For some reason SpatiaLite does something screwy with the Texas geometry here.  Also,
        # XXX it doesn't like the null intersection.
        if spatialite:
            qs = qs.exclude(name='Texas')
        else:
            qs = qs.intersection(geom)

        for c in qs:
            if oracle:
                # Should be able to execute the queries; however, they won't be the same
                # as GEOS (because Oracle doesn't use GEOS internally like PostGIS or
                # SpatiaLite).
                pass
            else:
                self.assertEqual(c.mpoly.difference(geom), c.difference)
                if not spatialite:
                    self.assertEqual(c.mpoly.intersection(geom), c.intersection)
                # Ordering might differ in collections
                self.assertSetEqual(set(g.wkt for g in c.mpoly.sym_difference(geom)),
                                    set(g.wkt for g in c.sym_difference))
                self.assertSetEqual(set(g.wkt for g in c.mpoly.union(geom)),
                                    set(g.wkt for g in c.union))

    @skipUnlessDBFeature("has_envelope_method")
    def test_envelope(self):
        "Testing the `envelope` GeoQuerySet method."
        countries = Country.objects.all().envelope()
        for country in countries:
            self.assertIsInstance(country.envelope, Polygon)

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_extent(self):
        """
        Testing the `Extent` aggregate.
        """
        # Reference query:
        # `SELECT ST_extent(point) FROM geoapp_city WHERE (name='Houston' or name='Dallas');`
        #   =>  BOX(-96.8016128540039 29.7633724212646,-95.3631439208984 32.7820587158203)
        expected = (-96.8016128540039, 29.7633724212646, -95.3631439208984, 32.782058715820)

        qs = City.objects.filter(name__in=('Houston', 'Dallas'))
        extent = qs.aggregate(Extent('point'))['point__extent']
        for val, exp in zip(extent, expected):
            self.assertAlmostEqual(exp, val, 4)
        self.assertIsNone(City.objects.filter(name=('Smalltown')).aggregate(Extent('point'))['point__extent'])

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_extent_with_limit(self):
        """
        Testing if extent supports limit.
        """
        extent1 = City.objects.all().aggregate(Extent('point'))['point__extent']
        extent2 = City.objects.all()[:3].aggregate(Extent('point'))['point__extent']
        self.assertNotEqual(extent1, extent2)

    @skipUnlessDBFeature("has_force_rhr_method")
    def test_force_rhr(self):
        "Testing GeoQuerySet.force_rhr()."
        rings = (
            ((0, 0), (5, 0), (0, 5), (0, 0)),
            ((1, 1), (1, 3), (3, 1), (1, 1)),
        )
        rhr_rings = (
            ((0, 0), (0, 5), (5, 0), (0, 0)),
            ((1, 1), (3, 1), (1, 3), (1, 1)),
        )
        State.objects.create(name='Foo', poly=Polygon(*rings))
        s = State.objects.force_rhr().get(name='Foo')
        self.assertEqual(rhr_rings, s.force_rhr.coords)

    @skipUnlessDBFeature("has_geohash_method")
    def test_geohash(self):
        "Testing GeoQuerySet.geohash()."
        # Reference query:
        # SELECT ST_GeoHash(point) FROM geoapp_city WHERE name='Houston';
        # SELECT ST_GeoHash(point, 5) FROM geoapp_city WHERE name='Houston';
        ref_hash = '9vk1mfq8jx0c8e0386z6'
        h1 = City.objects.geohash().get(name='Houston')
        h2 = City.objects.geohash(precision=5).get(name='Houston')
        self.assertEqual(ref_hash, h1.geohash)
        self.assertEqual(ref_hash[:5], h2.geohash)

    def test_geojson(self):
        "Testing GeoJSON output from the database using GeoQuerySet.geojson()."
        # Only PostGIS and SpatiaLite support GeoJSON.
        if not connection.ops.geojson:
            with self.assertRaises(NotImplementedError):
                Country.objects.all().geojson(field_name='mpoly')
            return

        pueblo_json = '{"type":"Point","coordinates":[-104.609252,38.255001]}'
        houston_json = (
            '{"type":"Point","crs":{"type":"name","properties":'
            '{"name":"EPSG:4326"}},"coordinates":[-95.363151,29.763374]}'
        )
        victoria_json = (
            '{"type":"Point","bbox":[-123.30519600,48.46261100,-123.30519600,48.46261100],'
            '"coordinates":[-123.305196,48.462611]}'
        )
        chicago_json = (
            '{"type":"Point","crs":{"type":"name","properties":{"name":"EPSG:4326"}},'
            '"bbox":[-87.65018,41.85039,-87.65018,41.85039],"coordinates":[-87.65018,41.85039]}'
        )
        if spatialite:
            victoria_json = (
                '{"type":"Point","bbox":[-123.305196,48.462611,-123.305196,48.462611],'
                '"coordinates":[-123.305196,48.462611]}'
            )

        # Precision argument should only be an integer
        with self.assertRaises(TypeError):
            City.objects.geojson(precision='foo')

        # Reference queries and values.
        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 0)
        # FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Pueblo';
        self.assertEqual(pueblo_json, City.objects.geojson().get(name='Pueblo').geojson)

        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 2) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Houston';
        # This time we want to include the CRS by using the `crs` keyword.
        self.assertEqual(houston_json, City.objects.geojson(crs=True, model_att='json').get(name='Houston').json)

        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 1) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Houston';
        # This time we include the bounding box by using the `bbox` keyword.
        self.assertEqual(victoria_json, City.objects.geojson(bbox=True).get(name='Victoria').geojson)

        # SELECT ST_AsGeoJson("geoapp_city"."point", 5, 3) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Chicago';
        # Finally, we set every available keyword.
        self.assertEqual(
            chicago_json,
            City.objects.geojson(bbox=True, crs=True, precision=5).get(name='Chicago').geojson
        )

    @skipUnlessDBFeature("has_gml_method")
    def test_gml(self):
        "Testing GML output from the database using GeoQuerySet.gml()."
        # Should throw a TypeError when trying to obtain GML from a
        # non-geometry field.
        qs = City.objects.all()
        with self.assertRaises(TypeError):
            qs.gml(field_name='name')
        ptown1 = City.objects.gml(field_name='point', precision=9).get(name='Pueblo')
        ptown2 = City.objects.gml(precision=9).get(name='Pueblo')

        if oracle:
            # No precision parameter for Oracle :-/
            gml_regex = re.compile(
                r'^<gml:Point srsName="EPSG:4326" xmlns:gml="http://www.opengis.net/gml">'
                r'<gml:coordinates decimal="\." cs="," ts=" ">-104.60925\d+,38.25500\d+ '
                r'</gml:coordinates></gml:Point>'
            )
        else:
            gml_regex = re.compile(
                r'^<gml:Point srsName="EPSG:4326"><gml:coordinates>'
                r'-104\.60925\d+,38\.255001</gml:coordinates></gml:Point>'
            )

        for ptown in [ptown1, ptown2]:
            self.assertTrue(gml_regex.match(ptown.gml))

        if postgis:
            self.assertIn('<gml:pos srsDimension="2">', City.objects.gml(version=3).get(name='Pueblo').gml)

    @skipUnlessDBFeature("has_kml_method")
    def test_kml(self):
        "Testing KML output from the database using GeoQuerySet.kml()."
        # Should throw a TypeError when trying to obtain KML from a
        #  non-geometry field.
        qs = City.objects.all()
        with self.assertRaises(TypeError):
            qs.kml('name')

        # Ensuring the KML is as expected.
        ptown1 = City.objects.kml(field_name='point', precision=9).get(name='Pueblo')
        ptown2 = City.objects.kml(precision=9).get(name='Pueblo')
        for ptown in [ptown1, ptown2]:
            self.assertEqual('<Point><coordinates>-104.609252,38.255001</coordinates></Point>', ptown.kml)

    def test_make_line(self):
        """
        Testing the `MakeLine` aggregate.
        """
        if not connection.features.supports_make_line_aggr:
            with self.assertRaises(NotImplementedError):
                City.objects.all().aggregate(MakeLine('point'))
            return

        # MakeLine on an inappropriate field returns simply None
        self.assertIsNone(State.objects.aggregate(MakeLine('poly'))['poly__makeline'])
        # Reference query:
        # SELECT AsText(ST_MakeLine(geoapp_city.point)) FROM geoapp_city;
        ref_line = GEOSGeometry(
            'LINESTRING(-95.363151 29.763374,-96.801611 32.782057,'
            '-97.521157 34.464642,174.783117 -41.315268,-104.609252 38.255001,'
            '-95.23506 38.971823,-87.650175 41.850385,-123.305196 48.462611)',
            srid=4326
        )
        # We check for equality with a tolerance of 10e-5 which is a lower bound
        # of the precisions of ref_line coordinates
        line = City.objects.aggregate(MakeLine('point'))['point__makeline']
        self.assertTrue(
            ref_line.equals_exact(line, tolerance=10e-5),
            "%s != %s" % (ref_line, line)
        )

    @skipUnlessDBFeature("has_num_geom_method")
    def test_num_geom(self):
        "Testing the `num_geom` GeoQuerySet method."
        # Both 'countries' only have two geometries.
        for c in Country.objects.num_geom():
            self.assertEqual(2, c.num_geom)

        for c in City.objects.filter(point__isnull=False).num_geom():
            # Oracle and PostGIS 2.0+ will return 1 for the number of
            # geometries on non-collections.
            self.assertEqual(1, c.num_geom)

    @skipUnlessDBFeature("supports_num_points_poly")
    def test_num_points(self):
        "Testing the `num_points` GeoQuerySet method."
        for c in Country.objects.num_points():
            self.assertEqual(c.mpoly.num_points, c.num_points)

        if not oracle:
            # Oracle cannot count vertices in Point geometries.
            for c in City.objects.num_points():
                self.assertEqual(1, c.num_points)

    @skipUnlessDBFeature("has_point_on_surface_method")
    def test_point_on_surface(self):
        "Testing the `point_on_surface` GeoQuerySet method."
        # Reference values.
        if oracle:
            # SELECT SDO_UTIL.TO_WKTGEOMETRY(SDO_GEOM.SDO_POINTONSURFACE(GEOAPP_COUNTRY.MPOLY, 0.05))
            # FROM GEOAPP_COUNTRY;
            ref = {'New Zealand': fromstr('POINT (174.616364 -36.100861)', srid=4326),
                   'Texas': fromstr('POINT (-103.002434 36.500397)', srid=4326),
                   }

        else:
            # Using GEOSGeometry to compute the reference point on surface values
            # -- since PostGIS also uses GEOS these should be the same.
            ref = {'New Zealand': Country.objects.get(name='New Zealand').mpoly.point_on_surface,
                   'Texas': Country.objects.get(name='Texas').mpoly.point_on_surface
                   }

        for c in Country.objects.point_on_surface():
            if spatialite:
                # XXX This seems to be a WKT-translation-related precision issue?
                tol = 0.00001
            else:
                tol = 0.000000001
            self.assertTrue(ref[c.name].equals_exact(c.point_on_surface, tol))

    @skipUnlessDBFeature("has_reverse_method")
    def test_reverse_geom(self):
        "Testing GeoQuerySet.reverse_geom()."
        coords = [(-95.363151, 29.763374), (-95.448601, 29.713803)]
        Track.objects.create(name='Foo', line=LineString(coords))
        t = Track.objects.reverse_geom().get(name='Foo')
        coords.reverse()
        self.assertEqual(tuple(coords), t.reverse_geom.coords)
        if oracle:
            with self.assertRaises(TypeError):
                State.objects.reverse_geom()

    @skipUnlessDBFeature("has_scale_method")
    def test_scale(self):
        "Testing the `scale` GeoQuerySet method."
        xfac, yfac = 2, 3
        tol = 5  # XXX The low precision tolerance is for SpatiaLite
        qs = Country.objects.scale(xfac, yfac, model_att='scaled')
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.scaled):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        self.assertAlmostEqual(c1[0] * xfac, c2[0], tol)
                        self.assertAlmostEqual(c1[1] * yfac, c2[1], tol)

    @skipUnlessDBFeature("has_snap_to_grid_method")
    def test_snap_to_grid(self):
        "Testing GeoQuerySet.snap_to_grid()."
        # Let's try and break snap_to_grid() with bad combinations of arguments.
        for bad_args in ((), range(3), range(5)):
            with self.assertRaises(ValueError):
                Country.objects.snap_to_grid(*bad_args)
        for bad_args in (('1.0',), (1.0, None), tuple(map(six.text_type, range(4)))):
            with self.assertRaises(TypeError):
                Country.objects.snap_to_grid(*bad_args)

        # Boundary for San Marino, courtesy of Bjorn Sandvik of thematicmapping.org
        # from the world borders dataset he provides.
        wkt = ('MULTIPOLYGON(((12.41580 43.95795,12.45055 43.97972,12.45389 43.98167,'
               '12.46250 43.98472,12.47167 43.98694,12.49278 43.98917,'
               '12.50555 43.98861,12.51000 43.98694,12.51028 43.98277,'
               '12.51167 43.94333,12.51056 43.93916,12.49639 43.92333,'
               '12.49500 43.91472,12.48778 43.90583,12.47444 43.89722,'
               '12.46472 43.89555,12.45917 43.89611,12.41639 43.90472,'
               '12.41222 43.90610,12.40782 43.91366,12.40389 43.92667,'
               '12.40500 43.94833,12.40889 43.95499,12.41580 43.95795)))')
        Country.objects.create(name='San Marino', mpoly=fromstr(wkt))

        # Because floating-point arithmetic isn't exact, we set a tolerance
        # to pass into GEOS `equals_exact`.
        tol = 0.000000001

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.1)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 44,12.5 44,12.5 43.9,12.4 43.9,12.4 44)))')
        self.assertTrue(ref.equals_exact(Country.objects.snap_to_grid(0.1).get(name='San Marino').snap_to_grid, tol))

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.05, 0.23)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 43.93,12.45 43.93,12.5 43.93,12.45 43.93,12.4 43.93)))')
        self.assertTrue(
            ref.equals_exact(Country.objects.snap_to_grid(0.05, 0.23).get(name='San Marino').snap_to_grid, tol)
        )

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.5, 0.17, 0.05, 0.23)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr(
            'MULTIPOLYGON(((12.4 43.87,12.45 43.87,12.45 44.1,12.5 44.1,12.5 43.87,12.45 43.87,12.4 43.87)))'
        )
        self.assertTrue(
            ref.equals_exact(
                Country.objects.snap_to_grid(0.05, 0.23, 0.5, 0.17).get(name='San Marino').snap_to_grid,
                tol
            )
        )

    @skipUnlessDBFeature("has_svg_method")
    def test_svg(self):
        "Testing SVG output using GeoQuerySet.svg()."

        with self.assertRaises(TypeError):
            City.objects.svg(precision='foo')
        # SELECT AsSVG(geoapp_city.point, 0, 8) FROM geoapp_city WHERE name = 'Pueblo';
        svg1 = 'cx="-104.609252" cy="-38.255001"'
        # Even though relative, only one point so it's practically the same except for
        # the 'c' letter prefix on the x,y values.
        svg2 = svg1.replace('c', '')
        self.assertEqual(svg1, City.objects.svg().get(name='Pueblo').svg)
        self.assertEqual(svg2, City.objects.svg(relative=5).get(name='Pueblo').svg)

    @skipUnlessDBFeature("has_transform_method")
    def test_transform(self):
        "Testing the transform() GeoQuerySet method."
        # Pre-transformed points for Houston and Pueblo.
        htown = fromstr('POINT(1947516.83115183 6322297.06040572)', srid=3084)
        ptown = fromstr('POINT(992363.390841912 481455.395105533)', srid=2774)
        prec = 3  # Precision is low due to version variations in PROJ and GDAL.

        # Asserting the result of the transform operation with the values in
        #  the pre-transformed points.  Oracle does not have the 3084 SRID.
        if not oracle:
            h = City.objects.transform(htown.srid).get(name='Houston')
            self.assertEqual(3084, h.point.srid)
            self.assertAlmostEqual(htown.x, h.point.x, prec)
            self.assertAlmostEqual(htown.y, h.point.y, prec)

        p1 = City.objects.transform(ptown.srid, field_name='point').get(name='Pueblo')
        p2 = City.objects.transform(srid=ptown.srid).get(name='Pueblo')
        for p in [p1, p2]:
            self.assertEqual(2774, p.point.srid)
            self.assertAlmostEqual(ptown.x, p.point.x, prec)
            self.assertAlmostEqual(ptown.y, p.point.y, prec)

    @skipUnlessDBFeature("has_translate_method")
    def test_translate(self):
        "Testing the `translate` GeoQuerySet method."
        xfac, yfac = 5, -23
        qs = Country.objects.translate(xfac, yfac, model_att='translated')
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.translated):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        # XXX The low precision is for SpatiaLite
                        self.assertAlmostEqual(c1[0] + xfac, c2[0], 5)
                        self.assertAlmostEqual(c1[1] + yfac, c2[1], 5)

    # TODO: Oracle can be made to pass if
    # union1 = union2 = fromstr('POINT (-97.5211570000000023 34.4646419999999978)')
    # but this seems unexpected and should be investigated to determine the cause.
    @skipUnlessDBFeature("has_unionagg_method")
    @no_oracle
    def test_unionagg(self):
        """
        Testing the `Union` aggregate.
        """
        tx = Country.objects.get(name='Texas').mpoly
        # Houston, Dallas -- Ordering may differ depending on backend or GEOS version.
        union1 = fromstr('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374)')
        union2 = fromstr('MULTIPOINT(-95.363151 29.763374,-96.801611 32.782057)')
        qs = City.objects.filter(point__within=tx)
        with self.assertRaises(ValueError):
            qs.aggregate(Union('name'))
        # Using `field_name` keyword argument in one query and specifying an
        # order in the other (which should not be used because this is
        # an aggregate method on a spatial column)
        u1 = qs.aggregate(Union('point'))['point__union']
        u2 = qs.order_by('name').aggregate(Union('point'))['point__union']
        tol = 0.00001
        self.assertTrue(union1.equals_exact(u1, tol) or union2.equals_exact(u1, tol))
        self.assertTrue(union1.equals_exact(u2, tol) or union2.equals_exact(u2, tol))
        qs = City.objects.filter(name='NotACity')
        self.assertIsNone(qs.aggregate(Union('point'))['point__union'])

    def test_within_subquery(self):
        """
        Test that using a queryset inside a geo lookup is working (using a subquery)
        (#14483).
        """
        tex_cities = City.objects.filter(
            point__within=Country.objects.filter(name='Texas').values('mpoly')).order_by('name')
        expected = ['Dallas', 'Houston']
        if not connection.features.supports_real_shape_operations:
            expected.append('Oklahoma City')
        self.assertEqual(
            list(tex_cities.values_list('name', flat=True)),
            expected
        )

    def test_non_concrete_field(self):
        NonConcreteModel.objects.create(point=Point(0, 0), name='name')
        list(NonConcreteModel.objects.all())

    def test_values_srid(self):
        for c, v in zip(City.objects.all(), City.objects.values()):
            self.assertEqual(c.point.srid, v['point'].srid)
