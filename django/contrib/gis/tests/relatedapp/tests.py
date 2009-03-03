import os, unittest
from django.contrib.gis.geos import *
from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models import F, Extent, Union
from django.contrib.gis.tests.utils import no_mysql, no_oracle
from django.conf import settings
from models import City, Location, DirectoryEntry, Parcel

cities = (('Aurora', 'TX', -97.516111, 33.058333),
          ('Roswell', 'NM', -104.528056, 33.387222),
          ('Kecksburg', 'PA',  -79.460734, 40.18476),
           )

class RelatedGeoModelTest(unittest.TestCase):
    
    def test01_setup(self):
        "Setting up for related model tests."
        for name, state, lon, lat in cities:
            loc = Location.objects.create(point=Point(lon, lat))
            c = City.objects.create(name=name, state=state, location=loc)

    @no_oracle # TODO: Fix select_related() problems w/Oracle and pagination.
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
        if SpatialBackend.postgis:
            tol = 3
        else:
            tol = 0
            
        def check_pnt(ref, pnt):
            self.assertAlmostEqual(ref.x, pnt.x, tol)
            self.assertAlmostEqual(ref.y, pnt.y, tol)
            self.assertEqual(ref.srid, pnt.srid)

        # Each city transformed to the SRID of their state plane coordinate system.
        transformed = (('Kecksburg', 2272, 'POINT(1490553.98959621 314792.131023984)'),
                       ('Roswell', 2257, 'POINT(481902.189077221 868477.766629735)'),
                       ('Aurora', 2276, 'POINT(2269923.2484839 7069381.28722222)'),
                       )

        for name, srid, wkt in transformed:
            # Doing this implicitly sets `select_related` select the location.
            # TODO: Fix why this breaks on Oracle.
            qs = list(City.objects.filter(name=name).transform(srid, field_name='location__point'))
            check_pnt(GEOSGeometry(wkt, srid), qs[0].location.point) 

    @no_mysql
    def test04_related_aggregate(self):
        "Testing the `extent` and `unionagg` GeoQuerySet aggregates on related geographic models."

        # This combines the Extent and Union aggregates into one query
        aggs = City.objects.aggregate(Extent('location__point'), Union('location__point'))

        # One for all locations, one that excludes Roswell.
        all_extent = (-104.528060913086, 33.0583305358887,-79.4607315063477, 40.1847610473633)
        txpa_extent = (-97.51611328125, 33.0583305358887,-79.4607315063477, 40.1847610473633)
        e1 = City.objects.extent(field_name='location__point')
        e2 = City.objects.exclude(name='Roswell').extent(field_name='location__point')
        e3 = aggs['location__point__extent']

        # The tolerance value is to four decimal places because of differences
        # between the Oracle and PostGIS spatial backends on the extent calculation.
        tol = 4
        for ref, e in [(all_extent, e1), (txpa_extent, e2), (all_extent, e3)]:
            for ref_val, e_val in zip(ref, e): self.assertAlmostEqual(ref_val, e_val, tol)

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
        if SpatialBackend.oracle:
            ref_u1 = MultiPoint(p3, p1, p2, srid=4326)
            ref_u2 = MultiPoint(p3, p2, srid=4326)
        else:
            ref_u1 = MultiPoint(p1, p2, p3, srid=4326)
            ref_u2 = MultiPoint(p2, p3, srid=4326)
        
        u1 = City.objects.unionagg(field_name='location__point')
        u2 = City.objects.exclude(name='Roswell').unionagg(field_name='location__point')
        u3 = aggs['location__point__union']

        self.assertEqual(ref_u1, u1)
        self.assertEqual(ref_u2, u2)
        self.assertEqual(ref_u1, u3)
        
    def test05_select_related_fk_to_subclass(self):
        "Testing that calling select_related on a query over a model with an FK to a model subclass works"
        # Regression test for #9752.
        l = list(DirectoryEntry.objects.all().select_related())

    def test6_f_expressions(self):
        "Testing F() expressions on GeometryFields."
        # Constructing a dummy parcel border and getting the City instance for
        # assigning the FK.
        b1 = GEOSGeometry('POLYGON((-97.501205 33.052520,-97.501205 33.052576,-97.501150 33.052576,-97.501150 33.052520,-97.501205 33.052520))', srid=4326)
        pcity = City.objects.get(name='Aurora')

        # First parcel has incorrect center point that is equal to the City;
        # it also has a second border that is different from the first as a
        # 100ft buffer around the City.
        c1 = pcity.location.point
        c2 = c1.transform(2276, clone=True)
        b2 = c2.buffer(100)
        p1 = Parcel.objects.create(name='P1', city=pcity, center1=c1, center2=c2, border1=b1, border2=b2)

        # Now creating a second Parcel where the borders are the same, just
        # in different coordinate systems.  The center points are also the
        # the same (but in different coordinate systems), and this time they
        # actually correspond to the centroid of the border.
        c1 = b1.centroid
        c2 = c1.transform(2276, clone=True)
        p2 = Parcel.objects.create(name='P2', city=pcity, center1=c1, center2=c2, border1=b1, border2=b1)

        # Should return the second Parcel, which has the center within the
        # border.
        qs = Parcel.objects.filter(center1__within=F('border1'))
        self.assertEqual(1, len(qs))
        self.assertEqual('P2', qs[0].name)
        
        if not SpatialBackend.mysql:
            # This time center2 is in a different coordinate system and needs
            # to be wrapped in transformation SQL.
            qs = Parcel.objects.filter(center2__within=F('border1'))
            self.assertEqual(1, len(qs))
            self.assertEqual('P2', qs[0].name)
        
        # Should return the first Parcel, which has the center point equal
        # to the point in the City ForeignKey.
        qs = Parcel.objects.filter(center1=F('city__location__point'))
        self.assertEqual(1, len(qs))
        self.assertEqual('P1', qs[0].name)

        if not SpatialBackend.mysql:
            # This time the city column should be wrapped in transformation SQL.
            qs = Parcel.objects.filter(border2__contains=F('city__location__point'))
            self.assertEqual(1, len(qs))
            self.assertEqual('P1', qs[0].name)

    # TODO: Related tests for KML, GML, and distance lookups.

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(RelatedGeoModelTest))
    return s
