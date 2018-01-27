from unittest import skipUnless

from django.contrib.gis.db.models import F, GeometryField, Value, functions
from django.contrib.gis.geos import Point, Polygon
from django.db import connection
from django.db.models import Count
from django.test import TestCase, skipUnlessDBFeature

from ..utils import postgis
from .models import City, ManyPointModel, MultiFields


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

    def test_update_from_other_field(self):
        p1 = Point(1, 1, srid=4326)
        p2 = Point(2, 2, srid=4326)
        obj = ManyPointModel.objects.create(
            point1=p1,
            point2=p2,
            point3=p2.transform(3857, clone=True),
        )
        # Updating a point to a point of the same SRID.
        ManyPointModel.objects.filter(pk=obj.pk).update(point2=F('point1'))
        obj.refresh_from_db()
        self.assertEqual(obj.point2, p1)
        # Updating a point to a point with a different SRID.
        if connection.features.supports_transform:
            ManyPointModel.objects.filter(pk=obj.pk).update(point3=F('point1'))
            obj.refresh_from_db()
            self.assertTrue(obj.point3.equals_exact(p1.transform(3857, clone=True), 0.1))

    def test_multiple_annotation(self):
        multi_field = MultiFields.objects.create(
            point=Point(1, 1),
            city=City.objects.get(name='Houston'),
            poly=Polygon(((1, 1), (1, 2), (2, 2), (2, 1), (1, 1))),
        )
        qs = City.objects.values('name').annotate(
            distance=functions.Distance('multifields__point', multi_field.city.point),
        ).annotate(count=Count('multifields'))
        self.assertTrue(qs.first())

    @skipUnlessDBFeature('has_Translate_function')
    def test_update_with_expression(self):
        city = City.objects.create(point=Point(1, 1, srid=4326))
        City.objects.filter(pk=city.pk).update(point=functions.Translate('point', 1, 1))
        city.refresh_from_db()
        self.assertEqual(city.point, Point(2, 2, srid=4326))
