from decimal import Decimal

from django.db.models.functions import Power
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class PowerTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('1.0'), n2=Decimal('-0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Power('n1', 'n2')).first()
        self.assertAlmostEqual(obj.n1_d, obj.n1**obj.n2)

    def test_float(self):
        FloatModel.objects.create(f1=2.3, f2=1.1)
        obj = FloatModel.objects.annotate(f1_d=Power('f1', 'f2')).first()
        self.assertAlmostEqual(float(obj.f1_d), obj.f1**obj.f2)

    def test_integer(self):
        IntegerModel.objects.create(small=-1, normal=20, big=3)
        obj = IntegerModel.objects.annotate(
            small_d=Power('small', 'normal'),
            normal_d=Power('normal', 'big'),
            big_d=Power('big', 'small'),
        ).first()
        self.assertAlmostEqual(obj.small_d, obj.small**obj.normal)
        self.assertAlmostEqual(obj.normal_d, obj.normal**obj.big)
        self.assertAlmostEqual(obj.big_d, obj.big**obj.small)
