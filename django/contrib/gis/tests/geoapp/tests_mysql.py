"""
 A limited test module is used for a limited spatial database.
"""
import os, unittest
from models import Country, City, State, Feature
from django.contrib.gis import gdal
from django.contrib.gis.geos import *
from django.core.exceptions import ImproperlyConfigured

class GeoModelTest(unittest.TestCase):
    
    def test01_initial_sql(self):
        "Testing geographic initial SQL."
        # Ensuring that data was loaded from initial SQL.
        self.assertEqual(2, Country.objects.count())
        self.assertEqual(8, City.objects.count())
        self.assertEqual(2, State.objects.count())

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

    def test03_contains_contained(self):
        "Testing the 'contained', 'contains', and 'bbcontains' lookup types."
        # Getting Texas, yes we were a country -- once ;)
        texas = Country.objects.get(name='Texas')
        
        # Seeing what cities are in Texas, should get Houston and Dallas,
        #  and Oklahoma City because MySQL 'within' only checks on the
        #  _bounding box_ of the Geometries.
        qs = City.objects.filter(point__within=texas.mpoly)
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

        # Pueblo is not contained in Texas or New Zealand.
        self.assertEqual(0, len(Country.objects.filter(mpoly__contains=pueblo.point))) # Query w/GEOSGeometry object

        # OK City is contained w/in bounding box of Texas.
        qs = Country.objects.filter(mpoly__bbcontains=okcity.point)
        self.assertEqual(1, len(qs))
        self.assertEqual('Texas', qs[0].name)

    def test04_disjoint(self):
        "Testing the `disjoint` lookup type."
        ptown = City.objects.get(name='Pueblo')
        qs1 = City.objects.filter(point__disjoint=ptown.point)
        self.assertEqual(7, qs1.count())
        # TODO: This query should work in MySQL, but it appears the
        # `MBRDisjoint` function doesn't work properly (I went down
        # to the SQL level for debugging and still got bogus answers).
        #qs2 = State.objects.filter(poly__disjoint=ptown.point)
        #self.assertEqual(1, qs2.count())
        #self.assertEqual('Kansas', qs2[0].name)

    def test05_equals(self):
        "Testing the 'same_as' and 'equals' lookup types."
        pnt = fromstr('POINT (-95.363151 29.763374)', srid=4326)
        c1 = City.objects.get(point=pnt)
        c2 = City.objects.get(point__same_as=pnt)
        c3 = City.objects.get(point__equals=pnt)
        for c in [c1, c2, c3]: self.assertEqual('Houston', c.name)

    def test06_geometryfield(self):
        "Testing GeometryField."
        f1 = Feature(name='Point', geom=Point(1, 1))
        f2 = Feature(name='LineString', geom=LineString((0, 0), (1, 1), (5, 5)))
        f3 = Feature(name='Polygon', geom=Polygon(LinearRing((0, 0), (0, 5), (5, 5), (5, 0), (0, 0))))
        f4 = Feature(name='GeometryCollection', 
                     geom=GeometryCollection(Point(2, 2), LineString((0, 0), (2, 2)), 
                                             Polygon(LinearRing((0, 0), (0, 5), (5, 5), (5, 0), (0, 0)))))
        f1.save()
        f2.save()
        f3.save()
        f4.save()

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
    
    def test07_mysql_limitations(self):
        "Testing that union(), kml(), gml() raise exceptions."
        self.assertRaises(ImproperlyConfigured, City.objects.union, Point(5, 23), field_name='point')
        self.assertRaises(ImproperlyConfigured, State.objects.all().kml, field_name='poly')
        self.assertRaises(ImproperlyConfigured, Country.objects.all().gml, field_name='mpoly')

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeoModelTest))
    return s
