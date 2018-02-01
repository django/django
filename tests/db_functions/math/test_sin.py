import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Sin
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class SinTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Sin('n1'), n2_d=Sin('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.sin(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.sin(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Sin('f1'), f2_d=Sin('f2')).first()
        self.assertAlmostEqual(float(obj.f1_d), math.sin(obj.f1))
        self.assertAlmostEqual(float(obj.f2_d), math.sin(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_d=Sin('small'),
            normal_d=Sin('normal'),
            big_d=Sin('big')
        ).first()
        self.assertAlmostEqual(obj.small_d, math.sin(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.sin(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.sin(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Sin, 'sin')
            DecimalModel.objects.create(n1=Decimal('5.4'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('0.1'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__sin__lt=0)
            self.assertQuerysetEqual(objs, [float(5.4)], lambda a: float(a.n1))
        finally:
            DecimalField._unregister_lookup(Sin, 'sin')
