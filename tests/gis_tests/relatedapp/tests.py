from django.contrib.gis.db.models import Collect, Count, Extent, F, MakeLine, Q, Union
from django.contrib.gis.db.models.functions import Centroid
from django.contrib.gis.geos import GEOSGeometry, MultiPoint, Point
from django.db import NotSupportedError, connection
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import override_settings
from django.utils import timezone

from .models import Article, Author, Book, City, DirectoryEntry, Event, Location, Parcel


class RelatedGeoModelTest(TestCase):
    fixtures = ["initial"]

    def test02_select_related(self):
        "Testing `select_related` on geographic models (see #7126)."
        qs1 = City.objects.order_by("id")
        qs2 = City.objects.order_by("id").select_related()
        qs3 = City.objects.order_by("id").select_related("location")

        # Reference data for what's in the fixtures.
        cities = (
            ("Aurora", "TX", -97.516111, 33.058333),
            ("Roswell", "NM", -104.528056, 33.387222),
            ("Kecksburg", "PA", -79.460734, 40.18476),
        )

        for qs in (qs1, qs2, qs3):
            for ref, c in zip(cities, qs):
                nm, st, lon, lat = ref
                self.assertEqual(nm, c.name)
                self.assertEqual(st, c.state)
                self.assertAlmostEqual(lon, c.location.point.x, 6)
                self.assertAlmostEqual(lat, c.location.point.y, 6)

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_related_extent_aggregate(self):
        "Testing the `Extent` aggregate on related geographic models."
        # This combines the Extent and Union aggregates into one query
        aggs = City.objects.aggregate(Extent("location__point"))

        # One for all locations, one that excludes New Mexico (Roswell).
        all_extent = (-104.528056, 29.763374, -79.460734, 40.18476)
        txpa_extent = (-97.516111, 29.763374, -79.460734, 40.18476)
        e1 = City.objects.aggregate(Extent("location__point"))[
            "location__point__extent"
        ]
        e2 = City.objects.exclude(state="NM").aggregate(Extent("location__point"))[
            "location__point__extent"
        ]
        e3 = aggs["location__point__extent"]

        # The tolerance value is to four decimal places because of differences
        # between the Oracle and PostGIS spatial backends on the extent
        # calculation.
        tol = 4
        for ref, e in [(all_extent, e1), (txpa_extent, e2), (all_extent, e3)]:
            for ref_val, e_val in zip(ref, e):
                self.assertAlmostEqual(ref_val, e_val, tol)

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_related_extent_annotate(self):
        """
        Test annotation with Extent GeoAggregate.
        """
        cities = City.objects.annotate(
            points_extent=Extent("location__point")
        ).order_by("name")
        tol = 4
        self.assertAlmostEqual(
            cities[0].points_extent, (-97.516111, 33.058333, -97.516111, 33.058333), tol
        )

    @skipUnlessDBFeature("supports_union_aggr")
    def test_related_union_aggregate(self):
        "Testing the `Union` aggregate on related geographic models."
        # This combines the Extent and Union aggregates into one query
        aggs = City.objects.aggregate(Union("location__point"))

        # These are the points that are components of the aggregate geographic
        # union that is returned. Each point # corresponds to City PK.
        p1 = Point(-104.528056, 33.387222)
        p2 = Point(-97.516111, 33.058333)
        p3 = Point(-79.460734, 40.18476)
        p4 = Point(-96.801611, 32.782057)
        p5 = Point(-95.363151, 29.763374)

        # The second union aggregate is for a union
        # query that includes limiting information in the WHERE clause (in
        # other words a `.filter()` precedes the call to `.aggregate(Union()`).
        ref_u1 = MultiPoint(p1, p2, p4, p5, p3, srid=4326)
        ref_u2 = MultiPoint(p2, p3, srid=4326)

        u1 = City.objects.aggregate(Union("location__point"))["location__point__union"]
        u2 = City.objects.exclude(
            name__in=("Roswell", "Houston", "Dallas", "Fort Worth"),
        ).aggregate(Union("location__point"))["location__point__union"]
        u3 = aggs["location__point__union"]
        self.assertEqual(type(u1), MultiPoint)
        self.assertEqual(type(u3), MultiPoint)

        # Ordering of points in the result of the union is not defined and
        # implementation-dependent (DB backend, GEOS version)
        self.assertEqual({p.ewkt for p in ref_u1}, {p.ewkt for p in u1})
        self.assertEqual({p.ewkt for p in ref_u2}, {p.ewkt for p in u2})
        self.assertEqual({p.ewkt for p in ref_u1}, {p.ewkt for p in u3})

    def test05_select_related_fk_to_subclass(self):
        """
        select_related on a query over a model with an FK to a model subclass.
        """
        # Regression test for #9752.
        list(DirectoryEntry.objects.select_related())

    def test06_f_expressions(self):
        "Testing F() expressions on GeometryFields."
        # Constructing a dummy parcel border and getting the City instance for
        # assigning the FK.
        b1 = GEOSGeometry(
            "POLYGON((-97.501205 33.052520,-97.501205 33.052576,"
            "-97.501150 33.052576,-97.501150 33.052520,-97.501205 33.052520))",
            srid=4326,
        )
        pcity = City.objects.get(name="Aurora")

        # First parcel has incorrect center point that is equal to the City;
        # it also has a second border that is different from the first as a
        # 100ft buffer around the City.
        c1 = pcity.location.point
        c2 = c1.transform(2276, clone=True)
        b2 = c2.buffer(100)
        Parcel.objects.create(
            name="P1", city=pcity, center1=c1, center2=c2, border1=b1, border2=b2
        )

        # Now creating a second Parcel where the borders are the same, just
        # in different coordinate systems. The center points are also the
        # same (but in different coordinate systems), and this time they
        # actually correspond to the centroid of the border.
        c1 = b1.centroid
        c2 = c1.transform(2276, clone=True)
        b2 = (
            b1
            if connection.features.supports_transform
            else b1.transform(2276, clone=True)
        )
        Parcel.objects.create(
            name="P2", city=pcity, center1=c1, center2=c2, border1=b1, border2=b2
        )

        # Should return the second Parcel, which has the center within the
        # border.
        qs = Parcel.objects.filter(center1__within=F("border1"))
        self.assertEqual(1, len(qs))
        self.assertEqual("P2", qs[0].name)

        # This time center2 is in a different coordinate system and needs to be
        # wrapped in transformation SQL.
        qs = Parcel.objects.filter(center2__within=F("border1"))
        if connection.features.supports_transform:
            self.assertEqual("P2", qs.get().name)
        else:
            msg = "This backend doesn't support the Transform function."
            with self.assertRaisesMessage(NotSupportedError, msg):
                list(qs)

        # Should return the first Parcel, which has the center point equal
        # to the point in the City ForeignKey.
        qs = Parcel.objects.filter(center1=F("city__location__point"))
        self.assertEqual(1, len(qs))
        self.assertEqual("P1", qs[0].name)

        # This time the city column should be wrapped in transformation SQL.
        qs = Parcel.objects.filter(border2__contains=F("city__location__point"))
        if connection.features.supports_transform:
            self.assertEqual("P1", qs.get().name)
        else:
            msg = "This backend doesn't support the Transform function."
            with self.assertRaisesMessage(NotSupportedError, msg):
                list(qs)

    def test07_values(self):
        "Testing values() and values_list()."
        gqs = Location.objects.all()
        gvqs = Location.objects.values()
        gvlqs = Location.objects.values_list()

        # Incrementing through each of the models, dictionaries, and tuples
        # returned by each QuerySet.
        for m, d, t in zip(gqs, gvqs, gvlqs):
            # The values should be Geometry objects and not raw strings
            # returned by the spatial database.
            self.assertIsInstance(d["point"], GEOSGeometry)
            self.assertIsInstance(t[1], GEOSGeometry)
            self.assertEqual(m.point, d["point"])
            self.assertEqual(m.point, t[1])

    @override_settings(USE_TZ=True)
    def test_07b_values(self):
        "Testing values() and values_list() with aware datetime. See #21565."
        Event.objects.create(name="foo", when=timezone.now())
        list(Event.objects.values_list("when"))

    def test08_defer_only(self):
        "Testing defer() and only() on Geographic models."
        qs = Location.objects.all().order_by("pk")
        def_qs = Location.objects.defer("point").order_by("pk")
        for loc, def_loc in zip(qs, def_qs):
            self.assertEqual(loc.point, def_loc.point)

    def test09_pk_relations(self):
        """
        Ensuring correct primary key column is selected across relations. See
        #10757.
        """
        # The expected ID values -- notice the last two location IDs
        # are out of order. Dallas and Houston have location IDs that differ
        # from their PKs -- this is done to ensure that the related location
        # ID column is selected instead of ID column for the city.
        city_ids = (1, 2, 3, 4, 5)
        loc_ids = (1, 2, 3, 5, 4)
        ids_qs = City.objects.order_by("id").values("id", "location__id")
        for val_dict, c_id, l_id in zip(ids_qs, city_ids, loc_ids):
            self.assertEqual(val_dict["id"], c_id)
            self.assertEqual(val_dict["location__id"], l_id)

    def test10_combine(self):
        "Testing the combination of two QuerySets (#10807)."
        buf1 = City.objects.get(name="Aurora").location.point.buffer(0.1)
        buf2 = City.objects.get(name="Kecksburg").location.point.buffer(0.1)
        qs1 = City.objects.filter(location__point__within=buf1)
        qs2 = City.objects.filter(location__point__within=buf2)
        combined = qs1 | qs2
        names = [c.name for c in combined]
        self.assertEqual(2, len(names))
        self.assertIn("Aurora", names)
        self.assertIn("Kecksburg", names)

    @skipUnlessDBFeature("allows_group_by_lob")
    def test12a_count(self):
        "Testing `Count` aggregate on geo-fields."
        # The City, 'Fort Worth' uses the same location as Dallas.
        dallas = City.objects.get(name="Dallas")

        # Count annotation should be 2 for the Dallas location now.
        loc = Location.objects.annotate(num_cities=Count("city")).get(
            id=dallas.location.id
        )
        self.assertEqual(2, loc.num_cities)

    def test12b_count(self):
        "Testing `Count` aggregate on non geo-fields."
        # Should only be one author (Trevor Paglen) returned by this query, and
        # the annotation should have 3 for the number of books, see #11087.
        # Also testing with a values(), see #11489.
        qs = Author.objects.annotate(num_books=Count("books")).filter(num_books__gt=1)
        vqs = (
            Author.objects.values("name")
            .annotate(num_books=Count("books"))
            .filter(num_books__gt=1)
        )
        self.assertEqual(1, len(qs))
        self.assertEqual(3, qs[0].num_books)
        self.assertEqual(1, len(vqs))
        self.assertEqual(3, vqs[0]["num_books"])

    @skipUnlessDBFeature("allows_group_by_lob")
    def test13c_count(self):
        "Testing `Count` aggregate with `.values()`. See #15305."
        qs = (
            Location.objects.filter(id=5)
            .annotate(num_cities=Count("city"))
            .values("id", "point", "num_cities")
        )
        self.assertEqual(1, len(qs))
        self.assertEqual(2, qs[0]["num_cities"])
        self.assertIsInstance(qs[0]["point"], GEOSGeometry)

    def test13_select_related_null_fk(self):
        "Testing `select_related` on a nullable ForeignKey."
        Book.objects.create(title="Without Author")
        b = Book.objects.select_related("author").get(title="Without Author")
        # Should be `None`, and not a 'dummy' model.
        self.assertIsNone(b.author)

    @skipUnlessDBFeature("supports_collect_aggr")
    def test_collect(self):
        """
        Testing the `Collect` aggregate.
        """
        # Reference query:
        # SELECT AsText(ST_Collect("relatedapp_location"."point"))
        # FROM "relatedapp_city"
        # LEFT OUTER JOIN
        #   "relatedapp_location" ON (
        #       "relatedapp_city"."location_id" = "relatedapp_location"."id"
        #   )
        # WHERE "relatedapp_city"."state" = 'TX';
        ref_geom = GEOSGeometry(
            "MULTIPOINT(-97.516111 33.058333,-96.801611 32.782057,"
            "-95.363151 29.763374,-96.801611 32.782057)"
        )

        coll = City.objects.filter(state="TX").aggregate(Collect("location__point"))[
            "location__point__collect"
        ]
        # Even though Dallas and Ft. Worth share same point, Collect doesn't
        # consolidate -- that's why 4 points in MultiPoint.
        self.assertEqual(4, len(coll))
        self.assertTrue(ref_geom.equals(coll))

    @skipUnlessDBFeature("supports_collect_aggr")
    def test_collect_filter(self):
        qs = City.objects.annotate(
            parcel_center=Collect(
                "parcel__center1",
                filter=~Q(parcel__name__icontains="ignore"),
            ),
            parcel_center_nonexistent=Collect(
                "parcel__center1",
                filter=Q(parcel__name__icontains="nonexistent"),
            ),
            parcel_center_single=Collect(
                "parcel__center1",
                filter=Q(parcel__name__contains="Alpha"),
            ),
        )
        city = qs.get(name="Aurora")
        self.assertEqual(
            city.parcel_center.wkt,
            GEOSGeometry("MULTIPOINT (1.7128 -2.006, 4.7128 5.006)"),
        )
        self.assertIsNone(city.parcel_center_nonexistent)
        self.assertIn(
            city.parcel_center_single.wkt,
            [
                GEOSGeometry("MULTIPOINT (1.7128 -2.006)"),
                GEOSGeometry("POINT (1.7128 -2.006)"),  # SpatiaLite collapse to POINT.
            ],
        )

    @skipUnlessDBFeature("has_Centroid_function", "supports_collect_aggr")
    def test_centroid_collect_filter(self):
        qs = City.objects.annotate(
            parcel_centroid=Centroid(
                Collect(
                    "parcel__center1",
                    filter=~Q(parcel__name__icontains="ignore"),
                )
            )
        )
        city = qs.get(name="Aurora")
        if connection.ops.mariadb:
            self.assertIsNone(city.parcel_centroid)
        else:
            self.assertIsInstance(city.parcel_centroid, Point)
            self.assertAlmostEqual(city.parcel_centroid[0], 3.2128, 4)
            self.assertAlmostEqual(city.parcel_centroid[1], 1.5, 4)

    @skipUnlessDBFeature("supports_make_line_aggr")
    def test_make_line_filter(self):
        qs = City.objects.annotate(
            parcel_line=MakeLine(
                "parcel__center1",
                filter=~Q(parcel__name__icontains="ignore"),
            ),
            parcel_line_nonexistent=MakeLine(
                "parcel__center1",
                filter=Q(parcel__name__icontains="nonexistent"),
            ),
        )
        city = qs.get(name="Aurora")
        self.assertIn(
            city.parcel_line.wkt,
            # The default ordering is flaky, so check both.
            [
                "LINESTRING (1.7128 -2.006, 4.7128 5.006)",
                "LINESTRING (4.7128 5.006, 1.7128 -2.006)",
            ],
        )
        self.assertIsNone(city.parcel_line_nonexistent)

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_extent_filter(self):
        qs = City.objects.annotate(
            parcel_border=Extent(
                "parcel__border1",
                filter=~Q(parcel__name__icontains="ignore"),
            ),
            parcel_border_nonexistent=Extent(
                "parcel__border1",
                filter=Q(parcel__name__icontains="nonexistent"),
            ),
            parcel_border_no_filter=Extent("parcel__border1"),
        )
        city = qs.get(name="Aurora")
        self.assertEqual(city.parcel_border, (0.0, 0.0, 22.0, 22.0))
        self.assertIsNone(city.parcel_border_nonexistent)
        self.assertEqual(city.parcel_border_no_filter, (0.0, 0.0, 32.0, 32.0))

    @skipUnlessDBFeature("supports_union_aggr")
    def test_union_filter(self):
        qs = City.objects.annotate(
            parcel_point_union=Union(
                "parcel__center2",
                filter=~Q(parcel__name__icontains="ignore"),
            ),
            parcel_point_nonexistent=Union(
                "parcel__center2",
                filter=Q(parcel__name__icontains="nonexistent"),
            ),
            parcel_point_union_single=Union(
                "parcel__center2",
                filter=Q(parcel__name__contains="Alpha"),
            ),
        )
        city = qs.get(name="Aurora")
        self.assertIn(
            city.parcel_point_union.wkt,
            [
                GEOSGeometry("MULTIPOINT (12.75 10.05, 3.7128 -5.006)"),
                GEOSGeometry("MULTIPOINT (3.7128 -5.006, 12.75 10.05)"),
            ],
        )
        self.assertIsNone(city.parcel_point_nonexistent)
        self.assertEqual(city.parcel_point_union_single.wkt, "POINT (3.7128 -5.006)")

    def test15_invalid_select_related(self):
        """
        select_related on the related name manager of a unique FK.
        """
        qs = Article.objects.select_related("author__article")
        # This triggers TypeError when `get_default_columns` has no
        # `local_only` keyword. The TypeError is swallowed if QuerySet is
        # actually evaluated as list generation swallows TypeError in CPython.
        str(qs.query)

    def test16_annotated_date_queryset(self):
        """
        Ensure annotated date querysets work if spatial backend is used.  See
        #14648.
        """
        birth_years = [
            dt.year
            for dt in list(
                Author.objects.annotate(num_books=Count("books")).dates("dob", "year")
            )
        ]
        birth_years.sort()
        self.assertEqual([1950, 1974], birth_years)

    # TODO: Related tests for KML, GML, and distance lookups.
