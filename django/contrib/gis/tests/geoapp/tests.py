import os, unittest
from models import Country, City, PennsylvaniaCity, State, Feature, MinusOneSRID
from django.contrib.gis import gdal
from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.geos import *
from django.contrib.gis.measure import Distance
from django.contrib.gis.tests.utils import no_oracle, no_postgis

# TODO: Some tests depend on the success/failure of previous tests, these should
# be decoupled.  This flag is an artifact of this problem, and makes debugging easier;
# specifically, the DISABLE flag will disables all tests, allowing problem tests to
# be examined individually.
DISABLE = False

class GeoModelTest(unittest.TestCase):

    def test01_initial_sql(self):
        "Testing geographic initial SQL."
        if DISABLE: return
        if SpatialBackend.oracle:
            # Oracle doesn't allow strings longer than 4000 characters
            # in SQL files, and I'm stumped on how to use Oracle BFILE's
            # in PLSQL, so we set up the larger geometries manually, rather
            # than relying on the initial SQL.

            # Routine for returning the path to the data files.
            data_dir = os.path.join(os.path.dirname(__file__), 'sql')
            def get_file(wkt_file):
                return os.path.join(data_dir, wkt_file)

            State(name='Colorado', poly=fromfile(get_file('co.wkt'))).save()
            State(name='Kansas', poly=fromfile(get_file('ks.wkt'))).save()
            Country(name='Texas', mpoly=fromfile(get_file('tx.wkt'))).save()
            Country(name='New Zealand', mpoly=fromfile(get_file('nz.wkt'))).save()

        # Ensuring that data was loaded from initial SQL.
        self.assertEqual(2, Country.objects.count())
        self.assertEqual(8, City.objects.count())

        # Oracle cannot handle NULL geometry values w/certain queries.
        if SpatialBackend.oracle: n_state = 2
        else: n_state = 3
        self.assertEqual(n_state, State.objects.count())

    def test02_proxy(self):
        "Testing Lazy-Geometry support (using the GeometryProxy)."
        if DISABLE: return
        ## Testing on a Point
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

        ## Testing on a Polygon
        shell = LinearRing((0, 0), (0, 100), (100, 100), (100, 0), (0, 0))
        inner = LinearRing((40, 40), (40, 60), (60, 60), (60, 40), (40, 40))

        # Creating a State object using a built Polygon
        ply = Polygon(shell, inner)
        nullstate = State(name='NullState', poly=ply)
        self.assertEqual(4326, nullstate.poly.srid) # SRID auto-set from None
        nullstate.save()

        ns = State.objects.get(name='NullState')
        self.assertEqual(ply, ns.poly)

        # Testing the `ogr` and `srs` lazy-geometry properties.
        if gdal.HAS_GDAL:
            self.assertEqual(True, isinstance(ns.poly.ogr, gdal.OGRGeometry))
            self.assertEqual(ns.poly.wkb, ns.poly.ogr.wkb)
            self.assertEqual(True, isinstance(ns.poly.srs, gdal.SpatialReference))
            self.assertEqual('WGS 84', ns.poly.srs.name)

        # Changing the interior ring on the poly attribute.
        new_inner = LinearRing((30, 30), (30, 70), (70, 70), (70, 30), (30, 30))
        ns.poly[1] = new_inner
        ply[1] = new_inner
        self.assertEqual(4326, ns.poly.srid)
        ns.save()
        self.assertEqual(ply, State.objects.get(name='NullState').poly)
        ns.delete()

    @no_oracle # Oracle does not support KML.
    def test03a_kml(self):
        "Testing KML output from the database using GeoManager.kml()."
        if DISABLE: return
        # Should throw a TypeError when trying to obtain KML from a
        #  non-geometry field.
        qs = City.objects.all()
        self.assertRaises(TypeError, qs.kml, 'name')

        # The reference KML depends on the version of PostGIS used
        # (the output stopped including altitude in 1.3.3).
        major, minor1, minor2 = SpatialBackend.version
        ref_kml1 = '<Point><coordinates>-104.609252,38.255001,0</coordinates></Point>'
        ref_kml2 = '<Point><coordinates>-104.609252,38.255001</coordinates></Point>'
        if major == 1:
            if minor1 > 3 or (minor1 == 3 and minor2 >= 3): ref_kml = ref_kml2
            else: ref_kml = ref_kml1
        else:
            ref_kml = ref_kml2

        # Ensuring the KML is as expected.
        ptown1 = City.objects.kml(field_name='point', precision=9).get(name='Pueblo')
        ptown2 = City.objects.kml(precision=9).get(name='Pueblo')
        for ptown in [ptown1, ptown2]:
            self.assertEqual(ref_kml, ptown.kml)

    def test03b_gml(self):
        "Testing GML output from the database using GeoManager.gml()."
        if DISABLE: return
        # Should throw a TypeError when tyring to obtain GML from a
        #  non-geometry field.
        qs = City.objects.all()
        self.assertRaises(TypeError, qs.gml, field_name='name')
        ptown1 = City.objects.gml(field_name='point', precision=9).get(name='Pueblo')
        ptown2 = City.objects.gml(precision=9).get(name='Pueblo')

        if SpatialBackend.oracle:
            # No precision parameter for Oracle :-/
            import re
            gml_regex = re.compile(r'<gml:Point srsName="SDO:4326" xmlns:gml="http://www.opengis.net/gml"><gml:coordinates decimal="\." cs="," ts=" ">-104.60925199\d+,38.25500\d+ </gml:coordinates></gml:Point>')
            for ptown in [ptown1, ptown2]:
                self.assertEqual(True, bool(gml_regex.match(ptown.gml)))
        else:
            for ptown in [ptown1, ptown2]:
                self.assertEqual('<gml:Point srsName="EPSG:4326"><gml:coordinates>-104.609252,38.255001</gml:coordinates></gml:Point>', ptown.gml)

    def test04_transform(self):
        "Testing the transform() GeoManager method."
        if DISABLE: return
        # Pre-transformed points for Houston and Pueblo.
        htown = fromstr('POINT(1947516.83115183 6322297.06040572)', srid=3084)
        ptown = fromstr('POINT(992363.390841912 481455.395105533)', srid=2774)
        prec = 3 # Precision is low due to version variations in PROJ and GDAL.

        # Asserting the result of the transform operation with the values in
        #  the pre-transformed points.  Oracle does not have the 3084 SRID.
        if not SpatialBackend.oracle:
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

    @no_oracle # Most likely can do this in Oracle, however, it is not yet implemented (patches welcome!)
    def test05_extent(self):
        "Testing the `extent` GeoQuerySet method."
        if DISABLE: return
        # Reference query:
        # `SELECT ST_extent(point) FROM geoapp_city WHERE (name='Houston' or name='Dallas');`
        #   =>  BOX(-96.8016128540039 29.7633724212646,-95.3631439208984 32.7820587158203)
        expected = (-96.8016128540039, 29.7633724212646, -95.3631439208984, 32.782058715820)

        qs = City.objects.filter(name__in=('Houston', 'Dallas'))
        extent = qs.extent()

        for val, exp in zip(extent, expected):
            self.assertAlmostEqual(exp, val, 8)

    @no_oracle
    def test06_make_line(self):
        "Testing the `make_line` GeoQuerySet method."
        if DISABLE: return
        # Ensuring that a `TypeError` is raised on models without PointFields.
        self.assertRaises(TypeError, State.objects.make_line)
        self.assertRaises(TypeError, Country.objects.make_line)
        # Reference query:
        # SELECT AsText(ST_MakeLine(geoapp_city.point)) FROM geoapp_city;
        ref_line = GEOSGeometry('LINESTRING(-95.363151 29.763374,-96.801611 32.782057,-97.521157 34.464642,174.783117 -41.315268,-104.609252 38.255001,-95.23506 38.971823,-87.650175 41.850385,-123.305196 48.462611)', srid=4326)
        self.assertEqual(ref_line, City.objects.make_line())

    def test09_disjoint(self):
        "Testing the `disjoint` lookup type."
        if DISABLE: return
        ptown = City.objects.get(name='Pueblo')
        qs1 = City.objects.filter(point__disjoint=ptown.point)
        self.assertEqual(7, qs1.count())

        if not SpatialBackend.postgis:
            # TODO: Do NULL columns bork queries on PostGIS?  The following
            # error is encountered:
            #  psycopg2.ProgrammingError: invalid memory alloc request size 4294957297
            qs2 = State.objects.filter(poly__disjoint=ptown.point)
            self.assertEqual(1, qs2.count())
            self.assertEqual('Kansas', qs2[0].name)

    def test10_contains_contained(self):
        "Testing the 'contained', 'contains', and 'bbcontains' lookup types."
        if DISABLE: return
        # Getting Texas, yes we were a country -- once ;)
        texas = Country.objects.get(name='Texas')

        # Seeing what cities are in Texas, should get Houston and Dallas,
        #  and Oklahoma City because 'contained' only checks on the
        #  _bounding box_ of the Geometries.
        if not SpatialBackend.oracle:
            qs = City.objects.filter(point__contained=texas.mpoly)
            self.assertEqual(3, qs.count())
            cities = ['Houston', 'Dallas', 'Oklahoma City']
            for c in qs: self.assertEqual(True, c.name in cities)

        # Pulling out some cities.
        houston = City.objects.get(name='Houston')
        wellington = City.objects.get(name='Wellington')
        pueblo = City.objects.get(name='Pueblo')
        okcity = City.objects.get(name='Oklahoma City')
        lawrence = City.objects.get(name='Lawrence')

        # Now testing contains on the countries using the points for
        #  Houston and Wellington.
        tx = Country.objects.get(mpoly__contains=houston.point) # Query w/GEOSGeometry
        nz = Country.objects.get(mpoly__contains=wellington.point.hex) # Query w/EWKBHEX
        ks = State.objects.get(poly__contains=lawrence.point)
        self.assertEqual('Texas', tx.name)
        self.assertEqual('New Zealand', nz.name)
        self.assertEqual('Kansas', ks.name)

        # Pueblo and Oklahoma City (even though OK City is within the bounding box of Texas)
        #  are not contained in Texas or New Zealand.
        self.assertEqual(0, len(Country.objects.filter(mpoly__contains=pueblo.point))) # Query w/GEOSGeometry object
        self.assertEqual(0, len(Country.objects.filter(mpoly__contains=okcity.point.wkt))) # Qeury w/WKT

        # OK City is contained w/in bounding box of Texas.
        if not SpatialBackend.oracle:
            qs = Country.objects.filter(mpoly__bbcontains=okcity.point)
            self.assertEqual(1, len(qs))
            self.assertEqual('Texas', qs[0].name)

    def test11_lookup_insert_transform(self):
        "Testing automatic transform for lookups and inserts."
        if DISABLE: return
        # San Antonio in 'WGS84' (SRID 4326)
        sa_4326 = 'POINT (-98.493183 29.424170)'
        wgs_pnt = fromstr(sa_4326, srid=4326) # Our reference point in WGS84

        # Oracle doesn't have SRID 3084, using 41157.
        if SpatialBackend.oracle:
            # San Antonio in 'Texas 4205, Southern Zone (1983, meters)' (SRID 41157)
            # Used the following Oracle SQL to get this value:
            #  SELECT SDO_UTIL.TO_WKTGEOMETRY(SDO_CS.TRANSFORM(SDO_GEOMETRY('POINT (-98.493183 29.424170)', 4326), 41157)) FROM DUAL;
            nad_wkt  = 'POINT (300662.034646583 5416427.45974934)'
            nad_srid = 41157
        else:
            # San Antonio in 'NAD83(HARN) / Texas Centric Lambert Conformal' (SRID 3084)
            nad_wkt = 'POINT (1645978.362408288754523 6276356.025927528738976)' # Used ogr.py in gdal 1.4.1 for this transform
            nad_srid = 3084

        # Constructing & querying with a point from a different SRID. Oracle
        # `SDO_OVERLAPBDYINTERSECT` operates differently from
        # `ST_Intersects`, so contains is used instead.
        nad_pnt = fromstr(nad_wkt, srid=nad_srid)
        if SpatialBackend.oracle:
            tx = Country.objects.get(mpoly__contains=nad_pnt)
        else:
            tx = Country.objects.get(mpoly__intersects=nad_pnt)
        self.assertEqual('Texas', tx.name)

        # Creating San Antonio.  Remember the Alamo.
        sa = City(name='San Antonio', point=nad_pnt)
        sa.save()

        # Now verifying that San Antonio was transformed correctly
        sa = City.objects.get(name='San Antonio')
        self.assertAlmostEqual(wgs_pnt.x, sa.point.x, 6)
        self.assertAlmostEqual(wgs_pnt.y, sa.point.y, 6)

        # If the GeometryField SRID is -1, then we shouldn't perform any
        # transformation if the SRID of the input geometry is different.
        m1 = MinusOneSRID(geom=Point(17, 23, srid=4326))
        m1.save()
        self.assertEqual(-1, m1.geom.srid)

    # Oracle does not support NULL geometries in its spatial index for
    # some routines (e.g., SDO_GEOM.RELATE).
    @no_oracle
    def test12_null_geometries(self):
        "Testing NULL geometry support, and the `isnull` lookup type."
        if DISABLE: return
        # Querying for both NULL and Non-NULL values.
        nullqs = State.objects.filter(poly__isnull=True)
        validqs = State.objects.filter(poly__isnull=False)

        # Puerto Rico should be NULL (it's a commonwealth unincorporated territory)
        self.assertEqual(1, len(nullqs))
        self.assertEqual('Puerto Rico', nullqs[0].name)

        # The valid states should be Colorado & Kansas
        self.assertEqual(2, len(validqs))
        state_names = [s.name for s in validqs]
        self.assertEqual(True, 'Colorado' in state_names)
        self.assertEqual(True, 'Kansas' in state_names)

        # Saving another commonwealth w/a NULL geometry.
        if not SpatialBackend.oracle:
            # TODO: Fix saving w/NULL geometry on Oracle.
            State(name='Northern Mariana Islands', poly=None).save()

    @no_oracle # No specific `left` or `right` operators in Oracle.
    def test13_left_right(self):
        "Testing the 'left' and 'right' lookup types."
        if DISABLE: return
        # Left: A << B => true if xmax(A) < xmin(B)
        # Right: A >> B => true if xmin(A) > xmax(B)
        #  See: BOX2D_left() and BOX2D_right() in lwgeom_box2dfloat4.c in PostGIS source.

        # Getting the borders for Colorado & Kansas
        co_border = State.objects.get(name='Colorado').poly
        ks_border = State.objects.get(name='Kansas').poly

        # Note: Wellington has an 'X' value of 174, so it will not be considered
        #  to the left of CO.

        # These cities should be strictly to the right of the CO border.
        cities = ['Houston', 'Dallas', 'San Antonio', 'Oklahoma City',
                  'Lawrence', 'Chicago', 'Wellington']
        qs = City.objects.filter(point__right=co_border)
        self.assertEqual(7, len(qs))
        for c in qs: self.assertEqual(True, c.name in cities)

        # These cities should be strictly to the right of the KS border.
        cities = ['Chicago', 'Wellington']
        qs = City.objects.filter(point__right=ks_border)
        self.assertEqual(2, len(qs))
        for c in qs: self.assertEqual(True, c.name in cities)

        # Note: Wellington has an 'X' value of 174, so it will not be considered
        #  to the left of CO.
        vic = City.objects.get(point__left=co_border)
        self.assertEqual('Victoria', vic.name)

        cities = ['Pueblo', 'Victoria']
        qs = City.objects.filter(point__left=ks_border)
        self.assertEqual(2, len(qs))
        for c in qs: self.assertEqual(True, c.name in cities)

    def test14_equals(self):
        "Testing the 'same_as' and 'equals' lookup types."
        if DISABLE: return
        pnt = fromstr('POINT (-95.363151 29.763374)', srid=4326)
        c1 = City.objects.get(point=pnt)
        c2 = City.objects.get(point__same_as=pnt)
        c3 = City.objects.get(point__equals=pnt)
        for c in [c1, c2, c3]: self.assertEqual('Houston', c.name)

    def test15_relate(self):
        "Testing the 'relate' lookup type."
        if DISABLE: return
        # To make things more interesting, we will have our Texas reference point in
        # different SRIDs.
        pnt1 = fromstr('POINT (649287.0363174 4177429.4494686)', srid=2847)
        pnt2 = fromstr('POINT(-98.4919715741052 29.4333344025053)', srid=4326)

        # Not passing in a geometry as first param shoud
        # raise a type error when initializing the GeoQuerySet
        self.assertRaises(TypeError, Country.objects.filter, mpoly__relate=(23, 'foo'))
        # Making sure the right exception is raised for the given
        # bad arguments.
        for bad_args, e in [((pnt1, 0), TypeError), ((pnt2, 'T*T***FF*', 0), ValueError)]:
            qs = Country.objects.filter(mpoly__relate=bad_args)
            self.assertRaises(e, qs.count)

        # Relate works differently for the different backends.
        if SpatialBackend.postgis:
            contains_mask = 'T*T***FF*'
            within_mask = 'T*F**F***'
            intersects_mask = 'T********'
        elif SpatialBackend.oracle:
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
        if not SpatialBackend.oracle:
            self.assertEqual('Texas', Country.objects.get(mpoly__relate=(pnt1, intersects_mask)).name)
            self.assertEqual('Texas', Country.objects.get(mpoly__relate=(pnt2, intersects_mask)).name)
            self.assertEqual('Lawrence', City.objects.get(point__relate=(ks.poly, intersects_mask)).name)

    def test16_createnull(self):
        "Testing creating a model instance and the geometry being None"
        if DISABLE: return
        c = City()
        self.assertEqual(c.point, None)

    def test17_unionagg(self):
        "Testing the `unionagg` (aggregate union) GeoManager method."
        if DISABLE: return
        tx = Country.objects.get(name='Texas').mpoly
        # Houston, Dallas, San Antonio -- Oracle has different order.
        union1 = fromstr('MULTIPOINT(-98.493183 29.424170,-96.801611 32.782057,-95.363151 29.763374)')
        union2 = fromstr('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374,-98.493183 29.424170)')
        qs = City.objects.filter(point__within=tx)
        self.assertRaises(TypeError, qs.unionagg, 'name')
        # Using `field_name` keyword argument in one query and specifying an
        # order in the other (which should not be used because this is
        # an aggregate method on a spatial column)
        u1 = qs.unionagg(field_name='point')
        u2 = qs.order_by('name').unionagg()
        tol = 0.00001
        if SpatialBackend.oracle:
            union = union2
        else:
            union = union1
        self.assertEqual(True, union.equals_exact(u1, tol))
        self.assertEqual(True, union.equals_exact(u2, tol))
        qs = City.objects.filter(name='NotACity')
        self.assertEqual(None, qs.unionagg(field_name='point'))

    def test18_geometryfield(self):
        "Testing GeometryField."
        if DISABLE: return
        Feature(name='Point', geom=Point(1, 1)).save()
        Feature(name='LineString', geom=LineString((0, 0), (1, 1), (5, 5))).save()
        Feature(name='Polygon', geom=Polygon(LinearRing((0, 0), (0, 5), (5, 5), (5, 0), (0, 0)))).save()
        Feature(name='GeometryCollection',
                geom=GeometryCollection(Point(2, 2), LineString((0, 0), (2, 2)),
                                        Polygon(LinearRing((0, 0), (0, 5), (5, 5), (5, 0), (0, 0))))).save()

        f_1 = Feature.objects.get(name='Point')
        self.assertEqual(True, isinstance(f_1.geom, Point))
        self.assertEqual((1.0, 1.0), f_1.geom.tuple)
        f_2 = Feature.objects.get(name='LineString')
        self.assertEqual(True, isinstance(f_2.geom, LineString))
        self.assertEqual(((0.0, 0.0), (1.0, 1.0), (5.0, 5.0)), f_2.geom.tuple)

        f_3 = Feature.objects.get(name='Polygon')
        self.assertEqual(True, isinstance(f_3.geom, Polygon))
        f_4 = Feature.objects.get(name='GeometryCollection')
        self.assertEqual(True, isinstance(f_4.geom, GeometryCollection))
        self.assertEqual(f_3.geom, f_4.geom[2])

    def test19_centroid(self):
        "Testing the `centroid` GeoQuerySet method."
        if DISABLE: return
        qs = State.objects.exclude(poly__isnull=True).centroid()
        if SpatialBackend.oracle: tol = 0.1
        else: tol = 0.000000001
        for s in qs:
            self.assertEqual(True, s.poly.centroid.equals_exact(s.centroid, tol))

    def test20_pointonsurface(self):
        "Testing the `point_on_surface` GeoQuerySet method."
        if DISABLE: return
        # Reference values.
        if SpatialBackend.oracle:
            # SELECT SDO_UTIL.TO_WKTGEOMETRY(SDO_GEOM.SDO_POINTONSURFACE(GEOAPP_COUNTRY.MPOLY, 0.05)) FROM GEOAPP_COUNTRY;
            ref = {'New Zealand' : fromstr('POINT (174.616364 -36.100861)', srid=4326),
                   'Texas' : fromstr('POINT (-103.002434 36.500397)', srid=4326),
                   }
        elif SpatialBackend.postgis:
            # Using GEOSGeometry to compute the reference point on surface values
            # -- since PostGIS also uses GEOS these should be the same.
            ref = {'New Zealand' : Country.objects.get(name='New Zealand').mpoly.point_on_surface,
                   'Texas' : Country.objects.get(name='Texas').mpoly.point_on_surface
                   }
        for cntry in Country.objects.point_on_surface():
            self.assertEqual(ref[cntry.name], cntry.point_on_surface)

    @no_oracle
    def test21_scale(self):
        "Testing the `scale` GeoQuerySet method."
        if DISABLE: return
        xfac, yfac = 2, 3
        qs = Country.objects.scale(xfac, yfac, model_att='scaled')
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.scaled):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        self.assertEqual(c1[0] * xfac, c2[0])
                        self.assertEqual(c1[1] * yfac, c2[1])

    @no_oracle
    def test22_translate(self):
        "Testing the `translate` GeoQuerySet method."
        if DISABLE: return
        xfac, yfac = 5, -23
        qs = Country.objects.translate(xfac, yfac, model_att='translated')
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.translated):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        self.assertEqual(c1[0] + xfac, c2[0])
                        self.assertEqual(c1[1] + yfac, c2[1])

    def test23_numgeom(self):
        "Testing the `num_geom` GeoQuerySet method."
        if DISABLE: return
        # Both 'countries' only have two geometries.
        for c in Country.objects.num_geom(): self.assertEqual(2, c.num_geom)
        for c in City.objects.filter(point__isnull=False).num_geom():
            # Oracle will return 1 for the number of geometries on non-collections,
            # whereas PostGIS will return None.
            if SpatialBackend.postgis: self.assertEqual(None, c.num_geom)
            else: self.assertEqual(1, c.num_geom)

    def test24_numpoints(self):
        "Testing the `num_points` GeoQuerySet method."
        if DISABLE: return
        for c in Country.objects.num_points(): self.assertEqual(c.mpoly.num_points, c.num_points)
        if SpatialBackend.postgis:
            # Oracle cannot count vertices in Point geometries.
            for c in City.objects.num_points(): self.assertEqual(1, c.num_points)

    @no_oracle
    def test25_geoset(self):
        "Testing the `difference`, `intersection`, `sym_difference`, and `union` GeoQuerySet methods."
        if DISABLE: return
        geom = Point(5, 23)
        for c in Country.objects.all().intersection(geom).difference(geom).sym_difference(geom).union(geom):
            self.assertEqual(c.mpoly.difference(geom), c.difference)
            self.assertEqual(c.mpoly.intersection(geom), c.intersection)
            self.assertEqual(c.mpoly.sym_difference(geom), c.sym_difference)
            self.assertEqual(c.mpoly.union(geom), c.union)

    def test26_inherited_geofields(self):
        "Test GeoQuerySet methods on inherited Geometry fields."
        # Creating a Pennsylvanian city.
        mansfield = PennsylvaniaCity.objects.create(name='Mansfield', county='Tioga', point='POINT(-77.071445 41.823881)')

        # All transformation SQL will need to be performed on the
        # _parent_ table.
        qs = PennsylvaniaCity.objects.transform(32128)

        self.assertEqual(1, qs.count())
        for pc in qs: self.assertEqual(32128, pc.point.srid)

from test_feeds import GeoFeedTest
from test_regress import GeoRegressionTests
from test_sitemaps import GeoSitemapTest

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeoModelTest))
    s.addTest(unittest.makeSuite(GeoFeedTest))
    s.addTest(unittest.makeSuite(GeoSitemapTest))
    s.addTest(unittest.makeSuite(GeoRegressionTests))
    return s
