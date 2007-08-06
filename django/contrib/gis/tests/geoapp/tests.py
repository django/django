import unittest
from models import Country, City, State
from django.contrib.gis.geos import fromstr, Point, LineString, LinearRing, Polygon

class GeoModelTest(unittest.TestCase):
    
    def test01_initial_sql(self):
        "Testing geographic initial SQL."

        # Ensuring that data was loaded from initial SQL.
        self.assertEqual(2, Country.objects.count())
        self.assertEqual(8, City.objects.count())
        self.assertEqual(3, State.objects.count())

    def test02_proxy(self):
        "Testing Lazy-Geometry support (using the GeometryProxy)."
        #### Testing on a Point
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

        #### Testing on a Polygon
        shell = LinearRing((0, 0), (0, 100), (100, 100), (100, 0), (0, 0))
        inner = LinearRing((40, 40), (40, 60), (60, 60), (60, 40), (40, 40))

        # Creating a State object using a built Polygon
        ply = Polygon(shell.clone(), inner.clone())
        nullstate = State(name='NullState', poly=ply)
        self.assertEqual(4326, nullstate.poly.srid) # SRID auto-set from None
        nullstate.save()
        self.assertEqual(ply, State.objects.get(name='NullState').poly)
        
        # Changing the interior ring on the poly attribute.
        new_inner = LinearRing((30, 30), (30, 70), (70, 70), (70, 30), (30, 30))
        nullstate.poly[1] = new_inner.clone()
        ply[1] = new_inner
        self.assertEqual(4326, nullstate.poly.srid)
        nullstate.save()
        self.assertEqual(ply, State.objects.get(name='NullState').poly)
        nullstate.delete()

    def test03_kml(self):
        "Testing KML output from the database using GeoManager.kml()."
        # Should throw an error trying to get KML from a non-geometry field.
        try:
            qs = City.objects.all().kml('name')
        except TypeError:
            pass
        else:
            self.fail('Expected a TypeError exception')

        # Ensuring the KML is as expected.
        ptown = City.objects.kml('point', precision=9).get(name='Pueblo')
        self.assertEqual('<Point><coordinates>-104.609252,38.255001,0</coordinates></Point>', ptown.kml)

    def test10_contains_contained(self):
        "Testing the 'contained' and 'contains' lookup types."

        # Getting Texas, yes we were a country -- once ;)
        texas = Country.objects.get(name='Texas')
        
        # Seeing what cities are in Texas, should get Houston and Dallas,
        #  and Oklahoma City because 'contained' only checks on the
        #  _bounding box_ of the Geometries.
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

    def test11_lookup_insert_transform(self):
        "Testing automatic transform for lookups and inserts."

        # San Antonio in 'WGS84' (SRID 4326) and 'NAD83(HARN) / Texas Centric Lambert Conformal' (SRID 3084)
        sa_4326 = 'POINT (-98.493183 29.424170)'
        sa_3084 = 'POINT (1645978.362408288754523 6276356.025927528738976)' # Used ogr.py in gdal 1.4.1 for this transform

        # Constructing & querying with a point from a different SRID
        wgs_pnt = fromstr(sa_4326, srid=4326) # Our reference point in WGS84
        nad_pnt = fromstr(sa_3084, srid=3084)
        tx = Country.objects.get(mpoly__intersects=nad_pnt)
        self.assertEqual('Texas', tx.name)
        
        # Creating San Antonio.  Remember the Alamo.
        sa = City(name='San Antonio', point=nad_pnt)
        sa.save()
        
        # Now verifying that San Antonio was transformed correctly
        sa = City.objects.get(name='San Antonio')
        self.assertAlmostEqual(wgs_pnt.x, sa.point.x, 6)
        self.assertAlmostEqual(wgs_pnt.y, sa.point.y, 6)

    def test12_null_geometries(self):
        "Testing NULL geometry support."

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
        nmi = State(name='Northern Mariana Islands', poly=None)
        nmi.save()
    
    def test13_left_right(self):
        "Testing the 'left' and 'right' lookup types."
        
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

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeoModelTest))
    return s
