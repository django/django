import math

from django.db.models.functions import Mod
from django.test import TestCase

<<<<<<< 6481064d067f4644786d98777438ff7f05dc8fb9:tests/db_functions/math/test_mod.py
from ..models import IntegerModel
=======
from .models import IntegerModel
>>>>>>> update tests and 2.1.txt:tests/db_functions/test_mod.py


class ModTests(TestCase):

    def test_integer(self):
        IntegerModel.objects.create(small=20, normal=15, big=1)
        obj = IntegerModel.objects.annotate(
            small_d=Mod('small', 'normal'),
            normal_d=Mod('normal', 'big'),
            big_d=Mod('big', 'small')).first()
        self.assertEqual(obj.small_d, math.fmod(obj.small, obj.normal))
        self.assertEqual(obj.normal_d, math.fmod(obj.normal, obj.big))
        self.assertEqual(obj.big_d, math.fmod(obj.big, obj.small))
