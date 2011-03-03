import re
from django.db import connection
from django.contrib.gis import gdal
from django.contrib.gis.geos import fromstr, GEOSGeometry, \
    Point, LineString, LinearRing, Polygon, GeometryCollection
from django.contrib.gis.measure import Distance
from django.contrib.gis.tests.utils import \
    no_mysql, no_oracle, no_spatialite, \
    mysql, oracle, postgis, spatialite
from django.test import TestCase

from models import Country, City, PennsylvaniaCity, State, Track

if not spatialite:
    from models import Feature, MinusOneSRID

class GeoModelTest(TestCase):

    def test01_fixtures(self):
        "Testing geographic model initialization from fixtures."
        # Ensuring that data was loaded from initial data fixtures.
        self.assertEqual(2, Country.objects.count())
        self.assertEqual(8, City.objects.count())
        self.assertEqual(2, State.objects.count())

    def test02_proxy(self):
        "Testing Lazy-Geometry support (using the GeometryProxy)."
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

    def test03a_kml(self):
        "Testing KML output from the database using GeoQuerySet.kml()."
        # Only PostGIS supports KML serialization
        if not postgis:
            self.assertRaises(NotImplementedError, State.objects.all().kml, field_name='poly')
            return

        # Should throw a TypeError when trying to obtain KML from a
        #  non-geometry field.
        qs = City.objects.all()
        self.assertRaises(TypeError, qs.kml, 'name')

        # The reference KML depends on the version of PostGIS used
        # (the output stopped including altitude in 1.3.3).
        if connection.ops.spatial_version >= (1, 3, 3):
            ref_kml =  '<Point><coordinates>-104.609252,38.255001</coordinates></Point>'
        else:
            ref_kml = '<Point><coordinates>-104.609252,38.255001,0</coordinates></Point>'

        # Ensuring the KML is as expected.
        ptown1 = City.objects.kml(field_name='point', precision=9).get(name='Pueblo')
        ptown2 = City.objects.kml(precision=9).get(name='Pueblo')
        for ptown in [ptown1, ptown2]:
            self.assertEqual(ref_kml, ptown.kml)

    def test03b_gml(self):
        "Testing GML output from the database using GeoQuerySet.gml()."
        if mysql or spatialite:
            self.assertRaises(NotImplementedError, Country.objects.all().gml, field_name='mpoly')
            return

        # Should throw a TypeError when tyring to obtain GML from a
        # non-geometry field.
        qs = City.objects.all()
        self.assertRaises(TypeError, qs.gml, field_name='name')
        ptown1 = City.objects.gml(field_name='point', precision=9).get(name='Pueblo')
        ptown2 = City.objects.gml(precision=9).get(name='Pueblo')

        if oracle:
            # No precision parameter for Oracle :-/
            gml_regex = re.compile(r'^<gml:Point srsName="SDO:4326" xmlns:gml="http://www.opengis.net/gml"><gml:coordinates decimal="\." cs="," ts=" ">-104.60925\d+,38.25500\d+ </gml:coordinates></gml:Point>')
            for ptown in [ptown1, ptown2]:
                self.assertTrue(gml_regex.match(ptown.gml))
        else:
            gml_regex = re.compile(r'^<gml:Point srsName="EPSG:4326"><gml:coordinates>-104\.60925\d+,38\.255001</gml:coordinates></gml:Point>')
            for ptown in [ptown1, ptown2]:
                self.assertTrue(gml_regex.match(ptown.gml))

    def test03c_geojson(self):
        "Testing GeoJSON output from the database using GeoQuerySet.geojson()."
        # Only PostGIS 1.3.4+ supports GeoJSON.
        if not connection.ops.geojson:
            self.assertRaises(NotImplementedError, Country.objects.all().geojson, field_name='mpoly')
            return

        if connection.ops.spatial_version >= (1, 4, 0):
            pueblo_json = '{"type":"Point","coordinates":[-104.609252,38.255001]}'
            houston_json = '{"type":"Point","crs":{"type":"name","properties":{"name":"EPSG:4326"}},"coordinates":[-95.363151,29.763374]}'
            victoria_json = '{"type":"Point","bbox":[-123.30519600,48.46261100,-123.30519600,48.46261100],"coordinates":[-123.305196,48.462611]}'
            chicago_json = '{"type":"Point","crs":{"type":"name","properties":{"name":"EPSG:4326"}},"bbox":[-87.65018,41.85039,-87.65018,41.85039],"coordinates":[-87.65018,41.85039]}'
        else:
            pueblo_json = '{"type":"Point","coordinates":[-104.60925200,38.25500100]}'
            houston_json = '{"type":"Point","crs":{"type":"EPSG","properties":{"EPSG":4326}},"coordinates":[-95.36315100,29.76337400]}'
            victoria_json = '{"type":"Point","bbox":[-123.30519600,48.46261100,-123.30519600,48.46261100],"coordinates":[-123.30519600,48.46261100]}'
            chicago_json = '{"type":"Point","crs":{"type":"EPSG","properties":{"EPSG":4326}},"bbox":[-87.65018,41.85039,-87.65018,41.85039],"coordinates":[-87.65018,41.85039]}'

        # Precision argument should only be an integer
        self.assertRaises(TypeError, City.objects.geojson, precision='foo')

        # Reference queries and values.
        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 0) FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Pueblo';
        self.assertEqual(pueblo_json, City.objects.geojson().get(name='Pueblo').geojson)

        # 1.3.x: SELECT ST_AsGeoJson("geoapp_city"."point", 8, 1) FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Houston';
        # 1.4.x: SELECT ST_AsGeoJson("geoapp_city"."point", 8, 2) FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Houston';
        # This time we want to include the CRS by using the `crs` keyword.
        self.assertEqual(houston_json, City.objects.geojson(crs=True, model_att='json').get(name='Houston').json)

        # 1.3.x: SELECT ST_AsGeoJson("geoapp_city"."point", 8, 2) FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Victoria';
        # 1.4.x: SELECT ST_AsGeoJson("geoapp_city"."point", 8, 1) FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Houston';
        # This time we include the bounding box by using the `bbox` keyword.
        self.assertEqual(victoria_json, City.objects.geojson(bbox=True).get(name='Victoria').geojson)

        # 1.(3|4).x: SELECT ST_AsGeoJson("geoapp_city"."point", 5, 3) FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Chicago';
        # Finally, we set every available keyword.
        self.assertEqual(chicago_json, City.objects.geojson(bbox=True, crs=True, precision=5).get(name='Chicago').geojson)

    def test03d_svg(self):
        "Testing SVG output using GeoQuerySet.svg()."
        if mysql or oracle:
            self.assertRaises(NotImplementedError, City.objects.svg)
            return

        self.assertRaises(TypeError, City.objects.svg, precision='foo')
        # SELECT AsSVG(geoapp_city.point, 0, 8) FROM geoapp_city WHERE name = 'Pueblo';
        svg1 = 'cx="-104.609252" cy="-38.255001"'
        # Even though relative, only one point so it's practically the same except for
        # the 'c' letter prefix on the x,y values.
        svg2 = svg1.replace('c', '')
        self.assertEqual(svg1, City.objects.svg().get(name='Pueblo').svg)
        self.assertEqual(svg2, City.objects.svg(relative=5).get(name='Pueblo').svg)

    @no_mysql
    def test04_transform(self):
        "Testing the transform() GeoManager method."
        # Pre-transformed points for Houston and Pueblo.
        htown = fromstr('POINT(1947516.83115183 6322297.06040572)', srid=3084)
        ptown = fromstr('POINT(992363.390841912 481455.395105533)', srid=2774)
        prec = 3 # Precision is low due to version variations in PROJ and GDAL.

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

    @no_mysql
    @no_spatialite # SpatiaLite does not have an Extent function
    def test05_extent(self):
        "Testing the `extent` GeoQuerySet method."
        # Reference query:
        # `SELECT ST_extent(point) FROM geoapp_city WHERE (name='Houston' or name='Dallas');`
        #   =>  BOX(-96.8016128540039 29.7633724212646,-95.3631439208984 32.7820587158203)
        expected = (-96.8016128540039, 29.7633724212646, -95.3631439208984, 32.782058715820)

        qs = City.objects.filter(name__in=('Houston', 'Dallas'))
        extent = qs.extent()

        for val, exp in zip(extent, expected):
            self.assertAlmostEqual(exp, val, 4)

    # Only PostGIS has support for the MakeLine aggregate.
    @no_mysql
    @no_oracle
    @no_spatialite
    def test06_make_line(self):
        "Testing the `make_line` GeoQuerySet method."
        # Ensuring that a `TypeError` is raised on models without PointFields.
        self.assertRaises(TypeError, State.objects.make_line)
        self.assertRaises(TypeError, Country.objects.make_line)
        # Reference query:
        # SELECT AsText(ST_MakeLine(geoapp_city.point)) FROM geoapp_city;
        ref_line = GEOSGeometry('LINESTRING(-95.363151 29.763374,-96.801611 32.782057,-97.521157 34.464642,174.783117 -41.315268,-104.609252 38.255001,-95.23506 38.971823,-87.650175 41.850385,-123.305196 48.462611)', srid=4326)
        self.assertEqual(ref_line, City.objects.make_line())

    @no_mysql
    def test09_disjoint(self):
        "Testing the `disjoint` lookup type."
        ptown = City.objects.get(name='Pueblo')
        qs1 = City.objects.filter(point__disjoint=ptown.point)
        self.assertEqual(7, qs1.count())

        qs2 = State.objects.filter(poly__disjoint=ptown.point)
        self.assertEqual(1, qs2.count())
        self.assertEqual('Kansas', qs2[0].name)

    def test10_contains_contained(self):
        "Testing the 'contained', 'contains', and 'bbcontains' lookup types."
        # Getting Texas, yes we were a country -- once ;)
        texas = Country.objects.get(name='Texas')

        # Seeing what cities are in Texas, should get Houston and Dallas,
        #  and Oklahoma City because 'contained' only checks on the
        #  _bounding box_ of the Geometries.
        if not oracle:
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
        self.assertEqual('Texas', tx.name)
        self.assertEqual('New Zealand', nz.name)

        # Spatialite 2.3 thinks that Lawrence is in Puerto Rico (a NULL geometry).
        if not spatialite:
            ks = State.objects.get(poly__contains=lawrence.point)
            self.assertEqual('Kansas', ks.name)

        # Pueblo and Oklahoma City (even though OK City is within the bounding box of Texas)
        # are not contained in Texas or New Zealand.
        self.assertEqual(0, len(Country.objects.filter(mpoly__contains=pueblo.point))) # Query w/GEOSGeometry object
        self.assertEqual((mysql and 1) or 0,
                         len(Country.objects.filter(mpoly__contains=okcity.point.wkt))) # Qeury w/WKT

        # OK City is contained w/in bounding box of Texas.
        if not oracle:
            qs = Country.objects.filter(mpoly__bbcontains=okcity.point)
            self.assertEqual(1, len(qs))
            self.assertEqual('Texas', qs[0].name)

    @no_mysql
    def test11_lookup_insert_transform(self):
        "Testing automatic transform for lookups and inserts."
        # San Antonio in 'WGS84' (SRID 4326)
        sa_4326 = 'POINT (-98.493183 29.424170)'
        wgs_pnt = fromstr(sa_4326, srid=4326) # Our reference point in WGS84

        # Oracle doesn't have SRID 3084, using 41157.
        if oracle:
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
        # SpatiaLite does not support missing SRID values.
        if not spatialite:
            m1 = MinusOneSRID(geom=Point(17, 23, srid=4326))
            m1.save()
            self.assertEqual(-1, m1.geom.srid)

    @no_mysql
    def test12_null_geometries(self):
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
        self.assertEqual(True, 'Colorado' in state_names)
        self.assertEqual(True, 'Kansas' in state_names)

        # Saving another commonwealth w/a NULL geometry.
        nmi = State.objects.create(name='Northern Mariana Islands', poly=None)
        self.assertEqual(nmi.poly, None)

        # Assigning a geomery and saving -- then UPDATE back to NULL.
        nmi.poly = 'POLYGON((0 0,1 0,1 1,1 0,0 0))'
        nmi.save()
        State.objects.filter(name='Northern Mariana Islands').update(poly=None)
        self.assertEqual(None, State.objects.get(name='Northern Mariana Islands').poly)

    # Only PostGIS has `left` and `right` lookup types.
    @no_mysql
    @no_oracle
    @no_spatialite
    def test13_left_right(self):
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
        pnt = fromstr('POINT (-95.363151 29.763374)', srid=4326)
        c1 = City.objects.get(point=pnt)
        c2 = City.objects.get(point__same_as=pnt)
        c3 = City.objects.get(point__equals=pnt)
        for c in [c1, c2, c3]: self.assertEqual('Houston', c.name)

    @no_mysql
    def test15_relate(self):
        "Testing the 'relate' lookup type."
        # To make things more interesting, we will have our Texas reference point in
        # different SRIDs.
        pnt1 = fromstr('POINT (649287.0363174 4177429.4494686)', srid=2847)
        pnt2 = fromstr('POINT(-98.4919715741052 29.4333344025053)', srid=4326)

        # Not passing in a geometry as first param shoud
        # raise a type error when initializing the GeoQuerySet
        self.assertRaises(ValueError, Country.objects.filter, mpoly__relate=(23, 'foo'))

        # Making sure the right exception is raised for the given
        # bad arguments.
        for bad_args, e in [((pnt1, 0), ValueError), ((pnt2, 'T*T***FF*', 0), ValueError)]:
            qs = Country.objects.filter(mpoly__relate=bad_args)
            self.assertRaises(e, qs.count)

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

    def test16_createnull(self):
        "Testing creating a model instance and the geometry being None"
        c = City()
        self.assertEqual(c.point, None)

    @no_mysql
    def test17_unionagg(self):
        "Testing the `unionagg` (aggregate union) GeoManager method."
        tx = Country.objects.get(name='Texas').mpoly
        # Houston, Dallas -- Oracle has different order.
        union1 = fromstr('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374)')
        union2 = fromstr('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374)')
        qs = City.objects.filter(point__within=tx)
        self.assertRaises(TypeError, qs.unionagg, 'name')
        # Using `field_name` keyword argument in one query and specifying an
        # order in the other (which should not be used because this is
        # an aggregate method on a spatial column)
        u1 = qs.unionagg(field_name='point')
        u2 = qs.order_by('name').unionagg()
        tol = 0.00001
        if oracle:
            union = union2
        else:
            union = union1
        self.assertEqual(True, union.equals_exact(u1, tol))
        self.assertEqual(True, union.equals_exact(u2, tol))
        qs = City.objects.filter(name='NotACity')
        self.assertEqual(None, qs.unionagg(field_name='point'))

    @no_spatialite # SpatiaLite does not support abstract geometry columns
    def test18_geometryfield(self):
        "Testing the general GeometryField."
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

    @no_mysql
    def test19_centroid(self):
        "Testing the `centroid` GeoQuerySet method."
        qs = State.objects.exclude(poly__isnull=True).centroid()
        if oracle:
            tol = 0.1
        elif spatialite:
            tol = 0.000001
        else:
            tol = 0.000000001
        for s in qs:
            self.assertEqual(True, s.poly.centroid.equals_exact(s.centroid, tol))

    @no_mysql
    def test20_pointonsurface(self):
        "Testing the `point_on_surface` GeoQuerySet method."
        # Reference values.
        if oracle:
            # SELECT SDO_UTIL.TO_WKTGEOMETRY(SDO_GEOM.SDO_POINTONSURFACE(GEOAPP_COUNTRY.MPOLY, 0.05)) FROM GEOAPP_COUNTRY;
            ref = {'New Zealand' : fromstr('POINT (174.616364 -36.100861)', srid=4326),
                   'Texas' : fromstr('POINT (-103.002434 36.500397)', srid=4326),
                   }

        elif postgis or spatialite:
            # Using GEOSGeometry to compute the reference point on surface values
            # -- since PostGIS also uses GEOS these should be the same.
            ref = {'New Zealand' : Country.objects.get(name='New Zealand').mpoly.point_on_surface,
                   'Texas' : Country.objects.get(name='Texas').mpoly.point_on_surface
                   }

        for c in Country.objects.point_on_surface():
            if spatialite:
                # XXX This seems to be a WKT-translation-related precision issue?
                tol = 0.00001
            else:
                tol = 0.000000001
            self.assertEqual(True, ref[c.name].equals_exact(c.point_on_surface, tol))

    @no_mysql
    @no_oracle
    def test21_scale(self):
        "Testing the `scale` GeoQuerySet method."
        xfac, yfac = 2, 3
        tol = 5 # XXX The low precision tolerance is for SpatiaLite
        qs = Country.objects.scale(xfac, yfac, model_att='scaled')
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.scaled):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        self.assertAlmostEqual(c1[0] * xfac, c2[0], tol)
                        self.assertAlmostEqual(c1[1] * yfac, c2[1], tol)

    @no_mysql
    @no_oracle
    def test22_translate(self):
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

    @no_mysql
    def test23_numgeom(self):
        "Testing the `num_geom` GeoQuerySet method."
        # Both 'countries' only have two geometries.
        for c in Country.objects.num_geom(): self.assertEqual(2, c.num_geom)
        for c in City.objects.filter(point__isnull=False).num_geom():
            # Oracle will return 1 for the number of geometries on non-collections,
            # whereas PostGIS will return None.
            if postgis:
                self.assertEqual(None, c.num_geom)
            else:
                self.assertEqual(1, c.num_geom)

    @no_mysql
    @no_spatialite # SpatiaLite can only count vertices in LineStrings
    def test24_numpoints(self):
        "Testing the `num_points` GeoQuerySet method."
        for c in Country.objects.num_points():
            self.assertEqual(c.mpoly.num_points, c.num_points)

        if not oracle:
            # Oracle cannot count vertices in Point geometries.
            for c in City.objects.num_points(): self.assertEqual(1, c.num_points)

    @no_mysql
    def test25_geoset(self):
        "Testing the `difference`, `intersection`, `sym_difference`, and `union` GeoQuerySet methods."
        geom = Point(5, 23)
        tol = 1
        qs = Country.objects.all().difference(geom).sym_difference(geom).union(geom)

        # XXX For some reason SpatiaLite does something screwey with the Texas geometry here.  Also,
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
                self.assertEqual(c.mpoly.sym_difference(geom), c.sym_difference)
                self.assertEqual(c.mpoly.union(geom), c.union)

    @no_mysql
    def test26_inherited_geofields(self):
        "Test GeoQuerySet methods on inherited Geometry fields."
        # Creating a Pennsylvanian city.
        mansfield = PennsylvaniaCity.objects.create(name='Mansfield', county='Tioga', point='POINT(-77.071445 41.823881)')

        # All transformation SQL will need to be performed on the
        # _parent_ table.
        qs = PennsylvaniaCity.objects.transform(32128)

        self.assertEqual(1, qs.count())
        for pc in qs: self.assertEqual(32128, pc.point.srid)

    @no_mysql
    @no_oracle
    @no_spatialite
    def test27_snap_to_grid(self):
        "Testing GeoQuerySet.snap_to_grid()."
        # Let's try and break snap_to_grid() with bad combinations of arguments.
        for bad_args in ((), range(3), range(5)):
            self.assertRaises(ValueError, Country.objects.snap_to_grid, *bad_args)
        for bad_args in (('1.0',), (1.0, None), tuple(map(unicode, range(4)))):
            self.assertRaises(TypeError, Country.objects.snap_to_grid, *bad_args)

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
        sm = Country.objects.create(name='San Marino', mpoly=fromstr(wkt))

        # Because floating-point arithmitic isn't exact, we set a tolerance
        # to pass into GEOS `equals_exact`.
        tol = 0.000000001

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.1)) FROM "geoapp_country" WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 44,12.5 44,12.5 43.9,12.4 43.9,12.4 44)))')
        self.assertTrue(ref.equals_exact(Country.objects.snap_to_grid(0.1).get(name='San Marino').snap_to_grid, tol))

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.05, 0.23)) FROM "geoapp_country" WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 43.93,12.45 43.93,12.5 43.93,12.45 43.93,12.4 43.93)))')
        self.assertTrue(ref.equals_exact(Country.objects.snap_to_grid(0.05, 0.23).get(name='San Marino').snap_to_grid, tol))

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.5, 0.17, 0.05, 0.23)) FROM "geoapp_country" WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 43.87,12.45 43.87,12.45 44.1,12.5 44.1,12.5 43.87,12.45 43.87,12.4 43.87)))')
        self.assertTrue(ref.equals_exact(Country.objects.snap_to_grid(0.05, 0.23, 0.5, 0.17).get(name='San Marino').snap_to_grid, tol))

    @no_mysql
    @no_spatialite
    def test28_reverse(self):
        "Testing GeoQuerySet.reverse_geom()."
        coords = [ (-95.363151, 29.763374), (-95.448601, 29.713803) ]
        Track.objects.create(name='Foo', line=LineString(coords))
        t = Track.objects.reverse_geom().get(name='Foo')
        coords.reverse()
        self.assertEqual(tuple(coords), t.reverse_geom.coords)
        if oracle:
            self.assertRaises(TypeError, State.objects.reverse_geom)

    @no_mysql
    @no_oracle
    @no_spatialite
    def test29_force_rhr(self):
        "Testing GeoQuerySet.force_rhr()."
        rings = ( ( (0, 0), (5, 0), (0, 5), (0, 0) ),
                  ( (1, 1), (1, 3), (3, 1), (1, 1) ),
                  )
        rhr_rings = ( ( (0, 0), (0, 5), (5, 0), (0, 0) ),
                      ( (1, 1), (3, 1), (1, 3), (1, 1) ),
                      )
        State.objects.create(name='Foo', poly=Polygon(*rings))
        s = State.objects.force_rhr().get(name='Foo')
        self.assertEqual(rhr_rings, s.force_rhr.coords)

    @no_mysql
    @no_oracle
    @no_spatialite
    def test30_geohash(self):
        "Testing GeoQuerySet.geohash()."
        if not connection.ops.geohash: return
        # Reference query:
        # SELECT ST_GeoHash(point) FROM geoapp_city WHERE name='Houston';
        # SELECT ST_GeoHash(point, 5) FROM geoapp_city WHERE name='Houston';
        ref_hash = '9vk1mfq8jx0c8e0386z6'
        h1 = City.objects.geohash().get(name='Houston')
        h2 = City.objects.geohash(precision=5).get(name='Houston')
        self.assertEqual(ref_hash, h1.geohash)
        self.assertEqual(ref_hash[:5], h2.geohash)

from test_feeds import GeoFeedTest
from test_regress import GeoRegressionTests
from test_sitemaps import GeoSitemapTest
