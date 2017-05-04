from unittest import skipUnless

from django.contrib.gis.db.models import GeometryField, Value, functions
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase, skipUnlessDBFeature

from ..utils import postgis
from .models import City


class GeoExpressionsTests(TestCase):
    fixtures = ['initial']

    def test_geometry_value_annotation(self):
        p = Point(1, 1, srid=4326)
        point = City.objects.annotate(p=Value(p, GeometryField(srid=4326))).first().p
        self.assertEqual(point, p)

    @skipUnlessDBFeature('supports_transform')
    def test_geometry_value_annotation_different_srid(self):
        p = Point(1, 1, srid=32140)
        point = City.objects.annotate(p=Value(p, GeometryField(srid=4326))).first().p
        self.assertTrue(point.equals_exact(p.transform(4326, clone=True), 10 ** -5))
        self.assertEqual(point.srid, 4326)

    @skipUnless(postgis, 'Only postgis has geography fields.')
    def test_geography_value(self):
        p = Polygon(((1, 1), (1, 2), (2, 2), (2, 1), (1, 1)))
        area = City.objects.annotate(a=functions.Area(Value(p, GeometryField(srid=4326, geography=True)))).first().a
        self.assertAlmostEqual(area.sq_km, 12305.1, 0)
