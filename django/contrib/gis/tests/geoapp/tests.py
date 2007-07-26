import unittest
from models import Country, City
from django.contrib.gis.geos import fromstr, Point

class GeoModelTest(unittest.TestCase):
    
    def test001_initial_sql(self):
        "Testing geographic initial SQL."

        # Ensuring that data was loaded from initial SQL.
        self.assertEqual(2, Country.objects.count())
        self.assertEqual(5, City.objects.count())
    
    def test002_contains_contained(self):
        "Testing the 'contained' and 'contains' lookup types."

        # Getting Texas, yes we were a country -- once ;)
        texas = Country.objects.get(name='Texas')
        
        # Seeing what cities are in Texas, should get Houston and Dallas,
        #  and Oklahoma City because 'contained' only checks on the
        #  _bounding box_ of the Geometries.
        qs = City.objects.filter(point__contained=texas.mpoly)
        self.assertEqual(3, qs.count())
        city_names = [c.name for c in qs]
        self.assertEqual(True, 'Houston' in city_names)
        self.assertEqual(True, 'Dallas' in city_names)
        self.assertEqual(True, 'Oklahoma City' in city_names)

        # Pulling out some cities.
        houston = City.objects.get(name='Houston')
        wellington = City.objects.get(name='Wellington')
        pueblo = City.objects.get(name='Pueblo')
        okcity = City.objects.get(name='Oklahoma City')

        # Now testing contains on the countries using the points for
        #  Houston and Wellington.
        tx = Country.objects.get(mpoly__contains=houston.point) # Query w/GEOSGeometry
        nz = Country.objects.get(mpoly__contains=wellington.point.hex) # Query w/EWKBHEX
        self.assertEqual('Texas', tx.name)
        self.assertEqual('New Zealand', nz.name)

        # Pueblo and Oklahoma City (even though OK City is within the bounding box of Texas)
        #  are not contained in Texas or New Zealand.
        self.assertEqual(0, len(Country.objects.filter(mpoly__contains=pueblo.point))) # Query w/GEOSGeometry object
        self.assertEqual(0, len(Country.objects.filter(mpoly__contains=okcity.point.wkt))) # Qeury w/WKT

    def test003_lookup_insert_transform(self):
        "Testing automatic transform for lookups and inserts."

        # San Antonio in WGS84 and NAD83(HARN) / Texas Centric Lambert Conformal
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

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeoModelTest))
    return s
