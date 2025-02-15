import math

from thibaud.db.models.functions import Pi
from thibaud.test import TestCase

from ..models import FloatModel


class PiTests(TestCase):
    def test(self):
        FloatModel.objects.create(f1=2.5, f2=15.9)
        obj = FloatModel.objects.annotate(pi=Pi()).first()
        self.assertIsInstance(obj.pi, float)
        self.assertAlmostEqual(obj.pi, math.pi, places=5)
