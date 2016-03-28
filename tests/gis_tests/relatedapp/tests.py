from __future__ import unicode_literals

from django.contrib.gis.db.models import Collect, Count, Extent, F, Union
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.geos import GEOSGeometry, MultiPoint, Point
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import override_settings
from django.utils import timezone

from ..utils import no_oracle
from .models import (
    Article, Author, Book, City, DirectoryEntry, Event, Location, Parcel,
)


@skipUnlessDBFeature("gis_enabled")
class RelatedGeoModelTest(TestCase):
    fixtures = ['initial']

    def test02_select_related(self):
        "Testing `select_related` on geographic models (see #7126)."
        qs1 = City.objects.order_by('id')
        qs2 = City.objects.order_by('id').select_related()
        qs3 = City.objects.order_by('id').select_related('location')

        # Reference data for what's in the fixtures.
        cities = (
            ('Aurora', 'TX', -97.516111, 33.058333),
            ('Roswell', 'NM', -104.528056, 33.387222),
            ('Kecksburg', 'PA', -79.460734, 40.18476),
        )

        for qs in (qs1, qs2, qs3):
            for ref, c in zip(cities, qs):
                nm, st, lon, lat = ref
                self.assertEqual(nm, c.name)
                self.assertEqual(st, c.state)
                self.assertEqual(Point(lon, lat), c.location.point)

    @skipUnlessDBFeature("has_transform_method")
    def test03_transform_related(self):
        "Testing the `transform` GeoQuerySet method on related geographic models."
        # All the transformations are to state plane coordinate systems using
        # US Survey Feet (thus a tolerance of 0 implies error w/in 1 survey foot).
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

        # Relations more than one level deep can be queried.
        self.assertEqual(list(Parcel.objects.transform(srid, field_name='city__location__point')), [])

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_related_extent_aggregate(self):
        "Testing the `Extent` aggregate on related geographic models."
        # This combines the Extent and Union aggregates into one query
        aggs = City.objects.aggregate(Extent('location__point'))

        # One for all locations, one that excludes New Mexico (Roswell).
        all_extent = (-104.528056, 29.763374, -79.460734, 40.18476)
        txpa_extent = (-97.516111, 29.763374, -79.460734, 40.18476)
        e1 = City.objects.aggregate(Extent('location__point'))['location__point__extent']
        e2 = City.objects.exclude(state='NM').aggregate(Extent('location__point'))['location__point__extent']
        e3 = aggs['location__point__extent']

        # The tolerance value is to four decimal places because of differences
        # between the Oracle and PostGIS spatial backends on the extent calculation.
        tol = 4
        for ref, e in [(all_extent, e1), (txpa_extent, e2), (all_extent, e3)]:
            for ref_val, e_val in zip(ref, e):
                self.assertAlmostEqual(ref_val, e_val, tol)

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_related_extent_annotate(self):
        """
        Test annotation with Extent GeoAggregate.
        """
        cities = City.objects.annotate(points_extent=Extent('location__point')).order_by('name')
        tol = 4
        self.assertAlmostEqual(
            cities[0].points_extent,
            (-97.516111, 33.058333, -97.516111, 33.058333),
            tol
        )

    @skipUnlessDBFeature("has_unionagg_method")
    def test_related_union_aggregate(self):
        "Testing the `Union` aggregate on related geographic models."
        # This combines the Extent and Union aggregates into one query
        aggs = City.objects.aggregate(Union('location__point'))

        # These are the points that are components of the aggregate geographic
        # union that is returned.  Each point # corresponds to City PK.
        p1 = Point(-104.528056, 33.387222)
        p2 = Point(-97.516111, 33.058333)
        p3 = Point(-79.460734, 40.18476)
        p4 = Point(-96.801611, 32.782057)
        p5 = Point(-95.363151, 29.763374)

        # The second union aggregate is for a union
        # query that includes limiting information in the WHERE clause (in other
        # words a `.filter()` precedes the call to `.aggregate(Union()`).
        ref_u1 = MultiPoint(p1, p2, p4, p5, p3, srid=4326)
        ref_u2 = MultiPoint(p2, p3, srid=4326)

        u1 = City.objects.aggregate(Union('location__point'))['location__point__union']
        u2 = City.objects.exclude(
            name__in=('Roswell', 'Houston', 'Dallas', 'Fort Worth'),
        ).aggregate(Union('location__point'))['location__point__union']
        u3 = aggs['location__point__union']
        self.assertEqual(type(u1), MultiPoint)
        self.assertEqual(type(u3), MultiPoint)

        # Ordering of points in the result of the union is not defined and
        # implementation-dependent (DB backend, GEOS version)
        self.assertSetEqual({p.ewkt for p in ref_u1}, {p.ewkt for p in u1})
        self.assertSetEqual({p.ewkt for p in ref_u2}, {p.ewkt for p in u2})
        self.assertSetEqual({p.ewkt for p in ref_u1}, {p.ewkt for p in u3})

    def test05_select_related_fk_to_subclass(self):
        "Testing that calling select_related on a query over a model with an FK to a model subclass works"
        # Regression test for #9752.
        list(DirectoryEntry.objects.all().select_related())

    def test06_f_expressions(self):
        "Testing F() expressions on GeometryFields."
        # Constructing a dummy parcel border and getting the City instance for
        # assigning the FK.
        b1 = GEOSGeometry(
            'POLYGON((-97.501205 33.052520,-97.501205 33.052576,'
            '-97.501150 33.052576,-97.501150 33.052520,-97.501205 33.052520))',
            srid=4326
        )
        pcity = City.objects.get(name='Aurora')

        # First parcel has incorrect center point that is equal to the City;
        # it also has a second border that is different from the first as a
        # 100ft buffer around the City.
        c1 = pcity.location.point
        c2 = c1.transform(2276, clone=True)
        b2 = c2.buffer(100)
        Parcel.objects.create(name='P1', city=pcity, center1=c1, center2=c2, border1=b1, border2=b2)

        # Now creating a second Parcel where the borders are the same, just
        # in different coordinate systems.  The center points are also the
        # same (but in different coordinate systems), and this time they
        # actually correspond to the centroid of the border.
        c1 = b1.centroid
        c2 = c1.transform(2276, clone=True)
        Parcel.objects.create(name='P2', city=pcity, center1=c1, center2=c2, border1=b1, border2=b1)

        # Should return the second Parcel, which has the center within the
        # border.
        qs = Parcel.objects.filter(center1__within=F('border1'))
        self.assertEqual(1, len(qs))
        self.assertEqual('P2', qs[0].name)

        if connection.features.supports_transform:
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

        if connection.features.supports_transform:
            # This time the city column should be wrapped in transformation SQL.
            qs = Parcel.objects.filter(border2__contains=F('city__location__point'))
            self.assertEqual(1, len(qs))
            self.assertEqual('P1', qs[0].name)

    def test07_values(self):
        "Testing values() and values_list() and GeoQuerySets."
        gqs = Location.objects.all()
        gvqs = Location.objects.values()
        gvlqs = Location.objects.values_list()

        # Incrementing through each of the models, dictionaries, and tuples
        # returned by the different types of GeoQuerySets.
        for m, d, t in zip(gqs, gvqs, gvlqs):
            # The values should be Geometry objects and not raw strings returned
            # by the spatial database.
            self.assertIsInstance(d['point'], Geometry)
            self.assertIsInstance(t[1], Geometry)
            self.assertEqual(m.point, d['point'])
            self.assertEqual(m.point, t[1])

    @override_settings(USE_TZ=True)
    def test_07b_values(self):
        "Testing values() and values_list() with aware datetime. See #21565."
        Event.objects.create(name="foo", when=timezone.now())
        list(Event.objects.values_list('when'))

    def test08_defer_only(self):
        "Testing defer() and only() on Geographic models."
        qs = Location.objects.all()
        def_qs = Location.objects.defer('point')
        for loc, def_loc in zip(qs, def_qs):
            self.assertEqual(loc.point, def_loc.point)

    def test09_pk_relations(self):
        "Ensuring correct primary key column is selected across relations. See #10757."
        # The expected ID values -- notice the last two location IDs
        # are out of order.  Dallas and Houston have location IDs that differ
        # from their PKs -- this is done to ensure that the related location
        # ID column is selected instead of ID column for the city.
        city_ids = (1, 2, 3, 4, 5)
        loc_ids = (1, 2, 3, 5, 4)
        ids_qs = City.objects.order_by('id').values('id', 'location__id')
        for val_dict, c_id, l_id in zip(ids_qs, city_ids, loc_ids):
            self.assertEqual(val_dict['id'], c_id)
            self.assertEqual(val_dict['location__id'], l_id)

    # TODO: fix on Oracle -- qs2 returns an empty result for an unknown reason
    @no_oracle
    def test10_combine(self):
        "Testing the combination of two GeoQuerySets.  See #10807."
        buf1 = City.objects.get(name='Aurora').location.point.buffer(0.1)
        buf2 = City.objects.get(name='Kecksburg').location.point.buffer(0.1)
        qs1 = City.objects.filter(location__point__within=buf1)
        qs2 = City.objects.filter(location__point__within=buf2)
        combined = qs1 | qs2
        names = [c.name for c in combined]
        self.assertEqual(2, len(names))
        self.assertIn('Aurora', names)
        self.assertIn('Kecksburg', names)

    # TODO: fix on Oracle -- get the following error because the SQL is ordered
    # by a geometry object, which Oracle apparently doesn't like:
    #  ORA-22901: cannot compare nested table or VARRAY or LOB attributes of an object type
    @no_oracle
    def test12a_count(self):
        "Testing `Count` aggregate on geo-fields."
        # The City, 'Fort Worth' uses the same location as Dallas.
        dallas = City.objects.get(name='Dallas')

        # Count annotation should be 2 for the Dallas location now.
        loc = Location.objects.annotate(num_cities=Count('city')).get(id=dallas.location.id)
        self.assertEqual(2, loc.num_cities)

    def test12b_count(self):
        "Testing `Count` aggregate on non geo-fields."
        # Should only be one author (Trevor Paglen) returned by this query, and
        # the annotation should have 3 for the number of books, see #11087.
        # Also testing with a values(), see #11489.
        qs = Author.objects.annotate(num_books=Count('books')).filter(num_books__gt=1)
        vqs = Author.objects.values('name').annotate(num_books=Count('books')).filter(num_books__gt=1)
        self.assertEqual(1, len(qs))
        self.assertEqual(3, qs[0].num_books)
        self.assertEqual(1, len(vqs))
        self.assertEqual(3, vqs[0]['num_books'])

    # TODO: fix on Oracle -- get the following error because the SQL is ordered
    # by a geometry object, which Oracle apparently doesn't like:
    #  ORA-22901: cannot compare nested table or VARRAY or LOB attributes of an object type
    @no_oracle
    def test13c_count(self):
        "Testing `Count` aggregate with `.values()`.  See #15305."
        qs = Location.objects.filter(id=5).annotate(num_cities=Count('city')).values('id', 'point', 'num_cities')
        self.assertEqual(1, len(qs))
        self.assertEqual(2, qs[0]['num_cities'])
        self.assertIsInstance(qs[0]['point'], GEOSGeometry)

    # TODO: The phantom model does appear on Oracle.
    @no_oracle
    def test13_select_related_null_fk(self):
        "Testing `select_related` on a nullable ForeignKey."
        Book.objects.create(title='Without Author')
        b = Book.objects.select_related('author').get(title='Without Author')
        # Should be `None`, and not a 'dummy' model.
        self.assertIsNone(b.author)

    @skipUnlessDBFeature("supports_collect_aggr")
    def test_collect(self):
        """
        Testing the `Collect` aggregate.
        """
        # Reference query:
        # SELECT AsText(ST_Collect("relatedapp_location"."point")) FROM "relatedapp_city" LEFT OUTER JOIN
        #    "relatedapp_location" ON ("relatedapp_city"."location_id" = "relatedapp_location"."id")
        #    WHERE "relatedapp_city"."state" = 'TX';
        ref_geom = GEOSGeometry(
            'MULTIPOINT(-97.516111 33.058333,-96.801611 32.782057,'
            '-95.363151 29.763374,-96.801611 32.782057)'
        )

        coll = City.objects.filter(state='TX').aggregate(Collect('location__point'))['location__point__collect']
        # Even though Dallas and Ft. Worth share same point, Collect doesn't
        # consolidate -- that's why 4 points in MultiPoint.
        self.assertEqual(4, len(coll))
        self.assertTrue(ref_geom.equals(coll))

    def test15_invalid_select_related(self):
        "Testing doing select_related on the related name manager of a unique FK. See #13934."
        qs = Article.objects.select_related('author__article')
        # This triggers TypeError when `get_default_columns` has no `local_only`
        # keyword.  The TypeError is swallowed if QuerySet is actually
        # evaluated as list generation swallows TypeError in CPython.
        str(qs.query)

    def test16_annotated_date_queryset(self):
        "Ensure annotated date querysets work if spatial backend is used.  See #14648."
        birth_years = [dt.year for dt in
                       list(Author.objects.annotate(num_books=Count('books')).dates('dob', 'year'))]
        birth_years.sort()
        self.assertEqual([1950, 1974], birth_years)

    # TODO: Related tests for KML, GML, and distance lookups.
