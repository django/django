import time
from unittest import skipIf

from django.contrib.gis.geos import GEOSGeometry, LineString, Point, Polygon
from django.contrib.gis.geos.libgeos import geos_version_tuple
from django.test import TestCase, skipUnlessDBFeature

from ..geo3d.models import Interstate3D, InterstateProj3D
from ..geo3d.tests import city_data, interstate_data
from .models import (
    City4D,
    Interstate4D,
    InterstateProj4D,
    MultiPoint4D,
    Point4D,
    Polygon4D,
)

epoch_time = int(time.time())


class GeoLoadingHelper:
    def _load_interstate_data(self):
        # Interstate (3D / 4D and Geographic/Projected variants)
        for name, line, _ in interstate_data:
            line_3d = GEOSGeometry(line, srid=4269)
            line_4d = LineString(
                [(*coord, epoch_time) for coord in line_3d.coords], srid=4269
            )

            # Creating a geographic and projected version of the
            # interstate in both 3D and 4D.
            Interstate3D.objects.create(name=name, line=line_3d)
            InterstateProj3D.objects.create(name=name, line=line_3d)
            Interstate4D.objects.create(name=name, line=line_4d)
            InterstateProj4D.objects.create(name=name, line=line_4d)

    def _load_city_data(self):
        for name, pnt_data in city_data:
            City4D.objects.create(
                name=name,
                point=Point(*pnt_data, epoch_time, srid=4326),
                pointg=Point(*pnt_data, epoch_time, srid=4326),
            )


@skipUnlessDBFeature("supports_4d_storage")
@skipIf(geos_version_tuple() < (3, 12), "GEOS >= 3.12.0 is required")
class Geo4DTest(GeoLoadingHelper, TestCase):
    """
    Only a subset of the PostGIS routines are 4D-enabled, and this TestCase
    tries to test the features that can handle 4D and that are also
    available within GeoDjango.
    """

    def test_4d_point(self):
        """
        Make sure data is 4D point and has expected M values --
        shouldn't change because of coordinate system.
        """
        self._load_city_data()
        for name, pnt_data in city_data:
            city = City4D.objects.get(name=name)
            # Testing both geometry and geography fields
            self.assertTrue(city.point.hasm)
            self.assertTrue(city.pointg.hasm)
            self.assertEqual(city.point.m, epoch_time)
            self.assertEqual(city.pointg.m, epoch_time)
            # Verify Z coordinate is preserved
            self.assertTrue(city.point.hasz)
            self.assertEqual(city.point.z, pnt_data[2])

    def test_4d_point_creation(self):
        """Test creating 4D points with various coordinate combinations."""
        # Test XYZM point
        p1 = Point(1.0, 2.0, 3.0, 100.0, srid=4326)
        Point4D.objects.create(point=p1)

        obj = Point4D.objects.get()
        self.assertTrue(obj.point.hasz)
        self.assertTrue(obj.point.hasm)
        self.assertEqual(obj.point.x, 1.0)
        self.assertEqual(obj.point.y, 2.0)
        self.assertEqual(obj.point.z, 3.0)
        self.assertEqual(obj.point.m, 100.0)

    def test_4d_linestring(self):
        """
        Make sure data is 4D linestring and has expected M values
        shouldn't change because of coordinate system.
        """
        self._load_interstate_data()
        for name, _, z in interstate_data:
            interstate = Interstate4D.objects.get(name=name)
            interstate_proj = InterstateProj4D.objects.get(name=name)
            for i in [interstate, interstate_proj]:
                m = tuple(i.line.m)
                self.assertTrue(i.line.hasm)
                self.assertTrue(all(x == epoch_time for x in m))
                self.assertEqual(len(z), len(m))

    @skipIf(geos_version_tuple() < (3, 14), "GEOS M support requires 3.14+")
    def test_4d_linestring_m_values(self):
        """Test that M values in linestrings are
        correctly stored and retrieved."""
        coords_with_m = [
            (0.0, 0.0, 0.0, 10.0),
            (1.0, 1.0, 1.0, 20.0),
            (2.0, 2.0, 2.0, 30.0),
        ]
        line = LineString(coords_with_m, srid=4269)
        Interstate4D.objects.create(name="Test Line", line=line)

        obj = Interstate4D.objects.get(name="Test Line")
        self.assertTrue(obj.line.hasm)
        self.assertTrue(obj.line.hasz)
        self.assertEqual(tuple(obj.line.m), (10.0, 20.0, 30.0))
        self.assertEqual(len(obj.line.coords), 3)

    @skipIf(geos_version_tuple() < (3, 14), "GEOS M support requires 3.14+")
    def test_4d_polygon(self):
        """Test that 4D polygons are correctly stored and retrieved."""
        # Create a square polygon with XYZM coordinates
        coords = [
            (0.0, 0.0, 0.0, 100.0),
            (0.0, 1.0, 1.0, 200.0),
            (1.0, 1.0, 2.0, 300.0),
            (1.0, 0.0, 3.0, 400.0),
            (0.0, 0.0, 0.0, 100.0),  # Close the ring
        ]
        poly = Polygon(coords, srid=32140)
        Polygon4D.objects.create(name="Test Polygon", poly=poly)

        obj = Polygon4D.objects.get(name="Test Polygon")
        self.assertTrue(obj.poly.hasm)
        self.assertTrue(obj.poly.hasz)
        # Check that M values are preserved
        #         m_values = tuple(obj.poly.coords[0])[::4]
        # Get every 4th element (M values)
        self.assertEqual(len(obj.poly.coords[0]), 5)

    def test_4d_multipoint(self):
        """Test that 4D MultiPoint geometries are correctly stored."""
        from django.contrib.gis.geos import MultiPoint

        points = [
            Point(0.0, 0.0, 0.0, 100.0),
            Point(1.0, 1.0, 1.0, 200.0),
            Point(2.0, 2.0, 2.0, 300.0),
        ]
        mpoint = MultiPoint(*points, srid=4326)
        MultiPoint4D.objects.create(mpoint=mpoint)

        obj = MultiPoint4D.objects.get()
        self.assertTrue(obj.mpoint.hasm)
        self.assertTrue(obj.mpoint.hasz)
        self.assertEqual(len(obj.mpoint), 3)
        # Check M values for each point
        for i, expected_m in enumerate([100.0, 200.0, 300.0]):
            self.assertEqual(obj.mpoint[i].m, expected_m)

    def test_4d_coordinate_dimensions(self):
        """Test that coordinate dimensions are correctly reported."""
        p = Point(1.0, 2.0, 3.0, 100.0, srid=4326)
        Point4D.objects.create(point=p)

        obj = Point4D.objects.get()
        self.assertEqual(obj.point.num_dims, 4)
        self.assertTrue(obj.point.hasz)
        self.assertTrue(obj.point.hasm)

    def test_4d_srid_preservation(self):
        """Test that SRID is preserved for 4D geometries."""
        p = Point(1.0, 2.0, 3.0, 100.0, srid=4326)
        Point4D.objects.create(point=p)

        obj = Point4D.objects.get()
        self.assertEqual(obj.point.srid, 4326)

    def test_4d_transform(self):
        """Test that 4D geometries can be transformed to different SRIDs."""
        # Create a point in SRID 4326
        p = Point(-95.363151, 29.763374, 18.0, epoch_time, srid=4326)
        City4D.objects.create(name="Transform Test", point=p, pointg=p)

        obj = City4D.objects.get(name="Transform Test")
        # Transform to Web Mercator (3857)
        transformed = obj.point.transform(3857, clone=True)

        # Verify M value is preserved after transformation
        self.assertTrue(transformed.hasm)
        self.assertEqual(transformed.m, epoch_time)
        self.assertNotEqual(transformed.x, p.x)  # Coordinates should change

    def test_4d_distance_calculation(self):
        """Test distance calculations with 4D geometries."""
        self._load_city_data()
        houston = City4D.objects.get(name="Houston")
        dallas = City4D.objects.get(name="Dallas")

        # Distance should work even with M dimension
        distance = houston.point.distance(dallas.point)
        self.assertGreater(distance, 0)

    def test_4d_intersection_operations(self):
        """Test that basic geometric operations work with 4D geometries."""
        line1 = LineString([(0, 0, 0, 100), (2, 2, 2, 200)], srid=4269)
        line2 = LineString([(0, 2, 0, 300), (2, 0, 2, 400)], srid=4269)

        Interstate4D.objects.create(name="Line1", line=line1)
        Interstate4D.objects.create(name="Line2", line=line2)

        obj1 = Interstate4D.objects.get(name="Line1")
        obj2 = Interstate4D.objects.get(name="Line2")

        # Test intersection
        self.assertTrue(obj1.line.intersects(obj2.line))

    def test_4d_query_filtering(self):
        """Test that we can query and filter 4D geometries."""
        self._load_city_data()

        # Get all cities
        cities = City4D.objects.all()
        self.assertGreater(len(cities), 0)

        # Verify all have M dimension
        for city in cities:
            self.assertTrue(city.point.hasm)
            self.assertEqual(city.point.m, epoch_time)

    def test_4d_ewkt_representation(self):
        """Test EWKT representation includes M dimension."""
        p = Point(1.0, 2.0, 3.0, 100.0, srid=4326)
        Point4D.objects.create(point=p)

        obj = Point4D.objects.get()
        ewkt = obj.point.ewkt
        # EWKT should contain SRID and all 4 coordinates
        self.assertIn("SRID=4326", ewkt)
        self.assertIn("POINT", ewkt)

    def test_4d_wkt_representation(self):
        """Test WKT representation of 4D geometries."""
        p = Point(1.0, 2.0, 3.0, 100.0, srid=4326)
        Point4D.objects.create(point=p)

        obj = Point4D.objects.get()
        wkt = obj.point.wkt
        # WKT should contain 4 coordinates
        self.assertIn("POINT ZM", wkt.upper())

    @skipIf(geos_version_tuple() < (3, 14), "GEOS M support requires 3.14+")
    def test_4d_coord_access(self):
        """Test direct coordinate access for 4D geometries."""
        coords = (1.0, 2.0, 3.0, 100.0)
        p = Point(*coords, srid=4326)
        Point4D.objects.create(point=p)

        obj = Point4D.objects.get()
        self.assertEqual(obj.point.x, 1.0)
        self.assertEqual(obj.point.y, 2.0)
        self.assertEqual(obj.point.z, 3.0)
        self.assertEqual(obj.point.m, 100.0)
        # Test tuple access
        self.assertEqual(obj.point.coords, coords)
