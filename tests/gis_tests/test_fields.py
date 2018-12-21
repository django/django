import copy

from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.sql import AreaField, DistanceField
from django.test import SimpleTestCase


class FieldsTests(SimpleTestCase):

    def test_area_field_deepcopy(self):
        field = AreaField(None)
        self.assertEqual(copy.deepcopy(field), field)

    def test_distance_field_deepcopy(self):
        field = DistanceField(None)
        self.assertEqual(copy.deepcopy(field), field)


class GeometryFieldTests(SimpleTestCase):
    def test_deconstruct_empty(self):
        field = GeometryField()
        *_, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {'srid': 4326})

    def test_deconstruct_values(self):
        field = GeometryField(
            srid=4067,
            dim=3,
            geography=True,
        )
        *_, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {
            'srid': 4067,
            'dim': 3,
            'geography': True,
        })
