import math

from django.db.models.functions import Pi
from django.test import TestCase

from .models import FloatModel


class PiTests(TestCase):

    def test_Pi(self):
        FloatModel.objects.create(f1=2.5, f2=15.9)
        obj = FloatModel.objects.annotate(pi=Pi()).first()
        self.assertAlmostEqual(obj.pi, math.pi, places=5)
