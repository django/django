import math
from decimal import Decimal

from django.db.models.functions import Mod
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class ModTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-9.9'), n2=Decimal('4.6'))
        obj = DecimalModel.objects.annotate(m=Mod('n1', 'n2')).first()
        self.assertAlmostEqual(obj.m, Decimal(math.fmod(obj.n1, obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-25, f2=0.33)
        obj = FloatModel.objects.annotate(m=Mod('f1', 'f2')).first()
        self.assertAlmostEqual(obj.m, math.fmod(obj.f1, obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=20, normal=15, big=1)
        obj = IntegerModel.objects.annotate(
            small_d=Mod('small', 'normal'),
            normal_d=Mod('normal', 'big'),
            big_d=Mod('big', 'small'),
        ).first()
        self.assertEqual(obj.small_d, math.fmod(obj.small, obj.normal))
        self.assertEqual(obj.normal_d, math.fmod(obj.normal, obj.big))
        self.assertEqual(obj.big_d, math.fmod(obj.big, obj.small))
