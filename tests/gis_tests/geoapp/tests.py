import tempfile
from io import StringIO

from django.contrib.gis import gdal
from django.contrib.gis.db.models import Extent, MakeLine, Union, functions
from django.contrib.gis.geos import (
    GeometryCollection, GEOSGeometry, LinearRing, LineString, MultiLineString,
    MultiPoint, MultiPolygon, Point, Polygon, fromstr,
)
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature

from ..utils import (
    mysql, no_oracle, oracle, postgis, skipUnlessGISLookup, spatialite,
)
from .models import (
    City, Country, Feature, MinusOneSRID, NonConcreteModel, PennsylvaniaCity,
    State, Track,
)


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
            with self.assertRaisesMessage(TypeError, 'Cannot set'):
                nullcity.point = bad

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
        self.assertNotEqual(Point(23, 5, srid=4326), City.objects.get(name='NullCity').point)
        nullcity.save()
        self.assertEqual(Point(23, 5, srid=4326), City.objects.get(name='NullCity').point)
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
        # San Antonio in 'WGS 84 / Pseudo-Mercator' (SRID 3857)
        other_srid_pnt = wgs_pnt.transform(3857, clone=True)
        # Constructing & querying with a point from a different SRID. Oracle
        # `SDO_OVERLAPBDYINTERSECT` operates differently from
        # `ST_Intersects`, so contains is used instead.
        if oracle:
            tx = Country.objects.get(mpoly__contains=other_srid_pnt)
        else:
            tx = Country.objects.get(mpoly__intersects=other_srid_pnt)
        self.assertEqual('Texas', tx.name)

        # Creating San Antonio.  Remember the Alamo.
        sa = City.objects.create(name='San Antonio', point=other_srid_pnt)

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
        self.assertIsNone(c.point)

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

    # TODO: fix on Oracle: ORA-22901: cannot compare nested table or VARRAY or
    # LOB attributes of an object type.
    @no_oracle
    @skipUnlessDBFeature("supports_transform")
    def test_inherited_geofields(self):
        "Database functions on inherited Geometry fields."
        # Creating a Pennsylvanian city.
        PennsylvaniaCity.objects.create(name='Mansfield', county='Tioga', point='POINT(-77.071445 41.823881)')

        # All transformation SQL will need to be performed on the
        # _parent_ table.
        qs = PennsylvaniaCity.objects.annotate(new_point=functions.Transform('point', srid=32128))

        self.assertEqual(1, qs.count())
        for pc in qs:
            self.assertEqual(32128, pc.new_point.srid)

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
        out = StringIO()
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
        self.assertEqual(original_data, list(City.objects.all().order_by('name')))

    @skipUnlessDBFeature("supports_empty_geometries")
    def test_empty_geometries(self):
        geometry_classes = [
            Point,
            LineString,
            LinearRing,
            Polygon,
            MultiPoint,
            MultiLineString,
            MultiPolygon,
            GeometryCollection,
        ]
        for klass in geometry_classes:
            g = klass(srid=4326)
            feature = Feature.objects.create(name='Empty %s' % klass.__name__, geom=g)
            feature.refresh_from_db()
            if klass is LinearRing:
                # LinearRing isn't representable in WKB, so GEOSGeomtry.wkb
                # uses LineString instead.
                g = LineString(srid=4326)
            self.assertEqual(feature.geom, g)
            self.assertEqual(feature.geom.srid, g.srid)


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
        qs = State.objects.all()
        if oracle or mysql:
            # Kansas has adjacent vertices with distance 6.99244813842e-12
            # which is smaller than the default Oracle tolerance.
            # It's invalid on MySQL too.
            qs = qs.exclude(name='Kansas')
            self.assertEqual(State.objects.filter(name='Kansas', poly__isvalid=False).count(), 1)
        self.assertEqual(qs.filter(poly__isvalid=False).count(), 1)
        self.assertEqual(qs.filter(poly__isvalid=True).count(), qs.count() - 1)

    @skipUnlessDBFeature("supports_left_right_lookups")
    def test_left_right_lookups(self):
        "Testing the 'left' and 'right' lookup types."
        # Left: A << B => true if xmax(A) < xmin(B)
        # Right: A >> B => true if xmin(A) > xmax(B)
        # See: BOX2D_left() and BOX2D_right() in lwgeom_box2dfloat4.c in PostGIS source.

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
        self.assertIsNone(nmi.poly)

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

        # Not passing in a geometry as first param raises a TypeError when
        # initializing the QuerySet.
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
class GeoQuerySetTest(TestCase):
    # TODO: GeoQuerySet is removed, organize these test better.
    fixtures = ['initial']

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

    @skipUnlessDBFeature('supports_union_aggr')
    def test_unionagg(self):
        """
        Testing the `Union` aggregate.
        """
        tx = Country.objects.get(name='Texas').mpoly
        # Houston, Dallas -- Ordering may differ depending on backend or GEOS version.
        union = GEOSGeometry('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374)')
        qs = City.objects.filter(point__within=tx)
        with self.assertRaises(ValueError):
            qs.aggregate(Union('name'))
        # Using `field_name` keyword argument in one query and specifying an
        # order in the other (which should not be used because this is
        # an aggregate method on a spatial column)
        u1 = qs.aggregate(Union('point'))['point__union']
        u2 = qs.order_by('name').aggregate(Union('point'))['point__union']
        self.assertTrue(union.equals(u1))
        self.assertTrue(union.equals(u2))
        qs = City.objects.filter(name='NotACity')
        self.assertIsNone(qs.aggregate(Union('point'))['point__union'])

    def test_within_subquery(self):
        """
        Using a queryset inside a geo lookup is working (using a subquery)
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
