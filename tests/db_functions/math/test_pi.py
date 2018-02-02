import math

from django.db.models.functions import Pi
from django.test import TestCase

<<<<<<< 6481064d067f4644786d98777438ff7f05dc8fb9:tests/db_functions/math/test_pi.py
from ..models import FloatModel
=======
from .models import FloatModel
>>>>>>> update tests and 2.1.txt:tests/db_functions/test_pi.py


class PiTests(TestCase):

    def test(self):
        FloatModel.objects.create(f1=2.5, f2=15.9)
        obj = FloatModel.objects.annotate(pi=Pi()).first()
        self.assertAlmostEqual(obj.pi, math.pi, places=5)
