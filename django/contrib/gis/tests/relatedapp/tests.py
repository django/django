import os, unittest
from django.contrib.gis.geos import *
from django.contrib.gis.tests.utils import no_mysql, postgis
from django.conf import settings
from models import City, Location

cities = (('Aurora', 'TX', -97.516111, 33.058333),
          ('Roswell', 'NM', -104.528056, 33.387222),
          ('Kecksburg', 'PA',  -79.460734, 40.18476),
           )

class RelatedGeoModelTest(unittest.TestCase):
    
    def test01_setup(self):
        "Setting up for related model tests."
        for name, state, lon, lat in cities:
            loc = Location(point=Point(lon, lat))
            loc.save()
            c = City(name=name, state=state, location=loc)
            c.save()
            
    def test02_select_related(self):
        "Testing `select_related` on geographic models (see #7126)."
        qs1 = City.objects.all()
        qs2 = City.objects.select_related()
        qs3 = City.objects.select_related('location')

        for qs in (qs1, qs2, qs3):
            for ref, c in zip(cities, qs):
                nm, st, lon, lat = ref
                self.assertEqual(nm, c.name)
                self.assertEqual(st, c.state)
                self.assertEqual(Point(lon, lat), c.location.point)
        
    @no_mysql
    def test03_transform_related(self):
        "Testing the `transform` GeoManager method on related geographic models."
        # All the transformations are to state plane coordinate systems using
        # US Survey Feet (thus a tolerance of 0 implies error w/in 1 survey foot).
        if postgis:
            tol = 3
            nqueries = 4 # +1 for `postgis_lib_version`
        else:
            tol = 0
            nqueries = 3
            
        def check_pnt(ref, pnt):
            self.assertAlmostEqual(ref.x, pnt.x, tol)
            self.assertAlmostEqual(ref.y, pnt.y, tol)

        # Turning on debug so we can manually verify the number of SQL queries issued.
        dbg = settings.DEBUG
        settings.DEBUG = True
        from django.db import connection

        # Each city transformed to the SRID of their state plane coordinate system.
        transformed = (('Kecksburg', 2272, 'POINT(1490553.98959621 314792.131023984)'),
                       ('Roswell', 2257, 'POINT(481902.189077221 868477.766629735)'),
                       ('Aurora', 2276, 'POINT(2269923.2484839 7069381.28722222)'),
                       )

        for name, srid, wkt in transformed:
            # Doing this implicitly sets `select_related` select the location.
            qs = list(City.objects.filter(name=name).transform('location__point', srid))
            check_pnt(GEOSGeometry(wkt), qs[0].location.point) 
        settings.DEBUG= dbg

        # Verifying the number of issued SQL queries.
        self.assertEqual(nqueries, len(connection.queries))

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(RelatedGeoModelTest))
    return s
