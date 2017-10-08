import copy

from django.contrib.gis.db.models.sql import AreaField, DistanceField
from django.test import SimpleTestCase


class FieldsTests(SimpleTestCase):

    def test_area_field_deepcopy(self):
        field = AreaField(None)
        self.assertEqual(copy.deepcopy(field), field)

    def test_distance_field_deepcopy(self):
        field = DistanceField(None)
        self.assertEqual(copy.deepcopy(field), field)
