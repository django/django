"""
Test for ticket #28341: GeometryField doesn't create GEOSGeometry objects
lazily anymore.

This test checks whether GeometryField values are converted to GEOSGeometry
immediately during queryset evaluation or lazily upon attribute access.
"""

from unittest import mock

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.geometry import GEOSGeometryBase
from django.test import TestCase

from .geoapp.models import City


class LazyGeometryTest(TestCase):
    """Test lazy loading of GeometryField values."""

    @classmethod
    def setUpTestData(cls):
        """Create test cities with point geometries."""
        cls.city1 = City.objects.create(name="TestCity1", point="POINT(0 0)")
        cls.city2 = City.objects.create(name="TestCity2", point="POINT(1 1)")

    def test_geometry_not_instantiated_during_query(self):
        """
        Test that GEOSGeometry is NOT instantiated during queryset evaluation.

        Expected behavior (lazy loading):
        - Backend converter should return raw WKB data
        - GEOSGeometry should be instantiated only on attribute access via
          SpatialProxy

        Current behavior (eager loading - BUG):
        - Backend converter creates GEOSGeometry immediately
        - SpatialProxy just returns the already-created object
        """
        # Mock the backend converter's GEOSGeometryBase instantiation
        with mock.patch(
            "django.contrib.gis.geos.geometry.GEOSGeometryBase.__new__",
            wraps=GEOSGeometryBase.__new__,
        ) as mock_geos_new:
            # Execute query - should NOT create GEOSGeometry if lazy
            city = City.objects.get(name="TestCity1")

            calls_during_query = mock_geos_new.call_count

            # Access the geometry attribute - SHOULD create GEOSGeometry
            city.point  # Trigger geometry access

            calls_after_access = mock_geos_new.call_count

            # For proper lazy loading:
            # - calls_during_query should be 0
            # - calls_after_access should be > 0
            self.assertEqual(
                calls_during_query,
                0,
                f"GEOSGeometry was created during query ({calls_during_query} times). "
                "Expected: 0 (lazy loading broken - ticket #28341)",
            )
            self.assertGreater(
                calls_after_access,
                0,
                "GEOSGeometry should be created on attribute access",
            )

    def test_raw_value_stored_in_instance_dict(self):
        """
        Test that raw database value (not GEOSGeometry) is stored after query.

        For lazy loading to work, SpatialProxy needs raw WKB data in
        instance.__dict__, not an already-converted GEOSGeometry object.
        """
        city = City.objects.get(name="TestCity1")

        # Check what's stored in the instance dictionary
        raw_value = city.__dict__.get("point")

        self.assertNotIsInstance(
            raw_value,
            (GEOSGeometry, GEOSGeometryBase),
            f"instance.__dict__['point'] contains a GEOSGeometry ({type(raw_value)}). "
            "Expected: raw database value (bytes/memoryview) for lazy loading.",
        )

        # Should be bytes, memoryview, or similar
        self.assertIn(
            type(raw_value).__name__,
            ["bytes", "memoryview", "buffer", "str"],
            f"Unexpected type in instance.__dict__: {type(raw_value)}",
        )

    def test_values_still_returns_geometry_objects(self):
        """
        Test that values() still returns GEOSGeometry objects (not raw values).

        This is the REQUIRED behavior - values() returns dicts without
        model instances, so converters MUST create GEOSGeometry objects. The
        fix should NOT break this.

        See: tests/gis_tests/relatedapp/tests.py::
        test07_values
        """
        result = City.objects.filter(name="TestCity1").values("point").first()

        # values() MUST return GEOSGeometry, not raw data
        self.assertIsInstance(
            result["point"],
            (GEOSGeometry, GEOSGeometryBase),
            "values() must return GEOSGeometry objects (converters required here)",
        )

    def test_values_list_still_returns_geometry_objects(self):
        """
        Test that values_list() still returns GEOSGeometry objects.

        Same as values() - converters are required for non-model-instance
        queries.
        """
        result = (
            City.objects.filter(name="TestCity1")
            .values_list("point", flat=True)
            .first()
        )

        self.assertIsInstance(
            result,
            (GEOSGeometry, GEOSGeometryBase),
            (
                "values_list() must return GEOSGeometry objects (converters required "
                "here)"
            ),
        )

    def test_multiple_objects_lazy_loading(self):
        """
        Test lazy loading with multiple objects in a queryset.

        This tests the performance reason for lazy loading: when fetching
        many objects but not accessing all geometry fields, geometries should
        only be created when accessed.
        """
        with mock.patch(
            "django.contrib.gis.geos.geometry.GEOSGeometryBase.__new__",
            wraps=GEOSGeometryBase.__new__,
        ) as mock_geos_new:
            # Fetch all cities - should NOT create geometries if lazy
            cities = list(City.objects.all())

            calls_after_query = mock_geos_new.call_count

            # Access only ONE city's geometry
            _ = cities[0].point

            calls_after_one_access = mock_geos_new.call_count

            # For lazy loading:
            # - No geometries created during query
            # - Only ONE geometry created on access
            self.assertEqual(
                calls_after_query,
                0,
                f"Geometries created during query: {calls_after_query}. "
                "Expected: 0 for lazy loading",
            )

            # At least one geometry should be created, but NOT all of them
            new_creations = calls_after_one_access - calls_after_query
            self.assertGreater(new_creations, 0, "Should create geometry on access")
            self.assertLess(
                new_creations,
                len(cities),
                f"Should only create {1} geometry, not all {len(cities)}",
            )

    def test_geometry_stored_as_raw_bytes(self):
        """
        Verify that geometry values are stored as raw bytes/memoryview in
        instance __dict__ before attribute access.

        This is a more thorough version testing the complete lazy loading
        cycle.
        """
        from django.contrib.gis.geos import Point

        city = City.objects.create(name="TestCity", point=Point(1.0, 2.0, srid=4326))

        # Fresh query
        fresh = City.objects.get(pk=city.pk)

        # Check internal storage BEFORE accessing .point
        raw_value = fresh.__dict__.get("point")

        # Should be raw bytes or memoryview, NOT GEOSGeometry
        self.assertIsInstance(
            raw_value,
            (bytes, memoryview),
            "Geometry should be stored as raw bytes before attribute access",
        )

        # Now access attribute
        point = fresh.point

        # Should convert to GEOSGeometry
        self.assertIsInstance(point, GEOSGeometry)

        # Check internal storage AFTER access
        converted_value = fresh.__dict__.get("point")

        # Should now be GEOSGeometry
        self.assertIsInstance(
            converted_value,
            GEOSGeometry,
            "Geometry should be converted to GEOSGeometry after access",
        )

    def test_queryset_iteration_does_not_instantiate_geometry(self):
        """
        Verify that iterating a queryset doesn't instantiate GEOSGeometry
        objects unless the geometry attribute is explicitly accessed.
        This is the primary performance benefit of lazy loading.
        """
        from django.contrib.gis.geos import Point

        # Create multiple cities
        for i in range(5):
            City.objects.create(
                name=f"City{i}", point=Point(float(i), float(i * 2), srid=4326)
            )

        # Track GEOSGeometry instantiations
        instantiation_count = 0
        original_init = GEOSGeometry.__init__

        def counting_init(self, *args, **kwargs):
            nonlocal instantiation_count
            instantiation_count += 1
            return original_init(self, *args, **kwargs)

        GEOSGeometry.__init__ = counting_init

        try:
            # Iterate queryset without accessing geometry
            cities = list(City.objects.all())

            # Should be zero instantiations
            self.assertEqual(
                instantiation_count,
                0,
                "GEOSGeometry should not be instantiated during queryset iteration",
            )

            # Now access one geometry
            _ = cities[0].point

            # Should be exactly one instantiation
            self.assertEqual(
                instantiation_count,
                1,
                "GEOSGeometry should be instantiated only when accessed",
            )
        finally:
            # Restore original
            GEOSGeometry.__init__ = original_init

    def test_annotation_with_f_expression(self):
        """Test that F() annotations return GEOSGeometry in values()"""
        from django.db.models import F

        result = list(
            City.objects.filter(name="TestCity1").annotate(p=F("point")).values("p")
        )
        value = result[0]["p"]
        self.assertIsInstance(
            value,
            (GEOSGeometry, GEOSGeometryBase),
            "F() annotation should return GEOSGeometry",
        )

    def test_defer_with_geometry(self):
        """Test that defer() works correctly with lazy loading"""
        city = City.objects.get(name="TestCity1")

        # Load with defer
        deferred_city = City.objects.defer("point").get(pk=city.pk)

        # Field should not be in __dict__ yet (deferred)
        self.assertNotIn("point", deferred_city.__dict__)

        # Access should load and convert
        point = deferred_city.point
        self.assertIsInstance(point, (GEOSGeometry, GEOSGeometryBase))

    def test_only_with_geometry(self):
        """Test that only() works correctly with lazy loading"""
        city = City.objects.get(name="TestCity1")

        # Load with only
        only_city = City.objects.only("id", "point").get(pk=city.pk)

        # Point should be loaded as raw bytes
        raw_value = only_city.__dict__.get("point")
        self.assertIsInstance(raw_value, (bytes, memoryview))

        # Access should convert
        point = only_city.point
        self.assertIsInstance(point, (GEOSGeometry, GEOSGeometryBase))

    def test_non_gis_fields_unaffected(self):
        """Test that non-GIS fields still work correctly in values()"""
        result = list(City.objects.filter(name="TestCity1").values("name", "id"))
        self.assertIsInstance(result[0]["name"], str)
        self.assertIsInstance(result[0]["id"], int)
