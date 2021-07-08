from django.db.models.functions import Random
from django.test import TestCase

from ..models import FloatModel


class RandomTests(TestCase):
    def test(self):
        FloatModel.objects.create()
        obj = FloatModel.objects.annotate(random=Random()).first()
        self.assertIsInstance(obj.random, float)
        self.assertGreaterEqual(obj.random, 0)
        self.assertLess(obj.random, 1)
