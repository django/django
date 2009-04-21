import os, unittest
from django.contrib.gis.geos import *
from django.contrib.gis.tests.utils import no_mysql, no_oracle, oracle, postgis
from django.conf import settings
from models import City, Location, DirectoryEntry

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
            
    @no_oracle # There are problems w/spatial Oracle pagination and select_related()
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
    @no_oracle # Pagination problem is implicated in this test as well.
    def test03_transform_related(self):
        "Testing the `transform` GeoQuerySet method on related geographic models."
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
            self.assertEqual(ref.srid, pnt.srid)

        # Turning on debug so we can manually verify the number of SQL queries issued.
        # DISABLED: the number of queries count testing mechanism is way too brittle.
        #dbg = settings.DEBUG
        #settings.DEBUG = True
        from django.db import connection

        # Each city transformed to the SRID of their state plane coordinate system.
        transformed = (('Kecksburg', 2272, 'POINT(1490553.98959621 314792.131023984)'),
                       ('Roswell', 2257, 'POINT(481902.189077221 868477.766629735)'),
                       ('Aurora', 2276, 'POINT(2269923.2484839 7069381.28722222)'),
                       )

        for name, srid, wkt in transformed:
            # Doing this implicitly sets `select_related` select the location.
            qs = list(City.objects.filter(name=name).transform(srid, field_name='location__point'))
            check_pnt(GEOSGeometry(wkt, srid), qs[0].location.point) 
        #settings.DEBUG= dbg

        # Verifying the number of issued SQL queries.
        #self.assertEqual(nqueries, len(connection.queries))

    @no_mysql
    @no_oracle
    def test04a_related_extent_aggregate(self):
        "Testing the `extent` GeoQuerySet aggregates on related geographic models."
        # One for all locations, one that excludes Roswell.
        all_extent = (-104.528060913086, 33.0583305358887,-79.4607315063477, 40.1847610473633)
        txpa_extent = (-97.51611328125, 33.0583305358887,-79.4607315063477, 40.1847610473633)
        e1 = City.objects.extent(field_name='location__point')
        e2 = City.objects.exclude(name='Roswell').extent(field_name='location__point')
        tol = 9
        for ref, e in [(all_extent, e1), (txpa_extent, e2)]:
            for ref_val, e_val in zip(ref, e): self.assertAlmostEqual(ref_val, e_val, tol)

    @no_mysql
    def test04b_related_union_aggregate(self):
        "Testing the `unionagg` GeoQuerySet aggregates on related geographic models."
        # These are the points that are components of the aggregate geographic
        # union that is returned.
        p1 = Point(-104.528056, 33.387222)
        p2 = Point(-97.516111, 33.058333)
        p3 = Point(-79.460734, 40.18476)

        # Creating the reference union geometry depending on the spatial backend,
        # as Oracle will have a different internal ordering of the component
        # geometries than PostGIS.  The second union aggregate is for a union
        # query that includes limiting information in the WHERE clause (in other
        # words a `.filter()` precedes the call to `.unionagg()`).
        if oracle:
            ref_u1 = MultiPoint(p3, p1, p2, srid=4326)
            ref_u2 = MultiPoint(p3, p2, srid=4326)
        else:
            ref_u1 = MultiPoint(p1, p2, p3, srid=4326)
            ref_u2 = MultiPoint(p2, p3, srid=4326)

        u1 = City.objects.unionagg(field_name='location__point')
        u2 = City.objects.exclude(name='Roswell').unionagg(field_name='location__point')

        self.assertEqual(ref_u1, u1)
        self.assertEqual(ref_u2, u2)
        
    def test05_select_related_fk_to_subclass(self):
        "Testing that calling select_related on a query over a model with an FK to a model subclass works"
        # Regression test for #9752.
        l = list(DirectoryEntry.objects.all().select_related())

    def test09_pk_relations(self):
        "Ensuring correct primary key column is selected across relations. See #10757."
        # Adding two more cities, but this time making sure that their location
        # ID values do not match their City ID values.
        loc1 = Location.objects.create(point='POINT (-95.363151 29.763374)')
        loc2 = Location.objects.create(point='POINT (-96.801611 32.782057)')
        dallas = City.objects.create(name='Dallas', location=loc2)
        houston = City.objects.create(name='Houston', location=loc1)

        # The expected ID values -- notice the last two location IDs
        # are out of order.  We want to make sure that the related
        # location ID column is selected instead of ID column for
        # the city.
        city_ids = (1, 2, 3, 4, 5)
        loc_ids = (1, 2, 3, 5, 4)
        ids_qs = City.objects.order_by('id').values('id', 'location__id')
        for val_dict, c_id, l_id in zip(ids_qs, city_ids, loc_ids):
            self.assertEqual(val_dict['id'], c_id)
            self.assertEqual(val_dict['location__id'], l_id)

    def test11_geoquery_pickle(self):
        "Ensuring GeoQuery objects are unpickled correctly.  See #10839."
        import pickle
        from django.contrib.gis.db.models.sql import GeoQuery
        qs = City.objects.all()
        q_str = pickle.dumps(qs.query)
        q = pickle.loads(q_str)
        self.assertEqual(GeoQuery, q.__class__)

    # TODO: Related tests for KML, GML, and distance lookups.
        
def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(RelatedGeoModelTest))
    return s
