import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Radians
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class RadiansTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Radians('n1'), n2_d=Radians('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.radians(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.radians(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Radians('f1'), f2_d=Radians('f2')).first()
        self.assertAlmostEqual(float(obj.f1_d), math.radians(obj.f1))
        self.assertAlmostEqual(float(obj.f2_d), math.radians(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_d=Radians('small'),
            normal_d=Radians('normal'),
            big_d=Radians('big'),
        ).first()
        self.assertAlmostEqual(obj.small_d, math.radians(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.radians(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.radians(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Radians)
            DecimalModel.objects.create(n1=Decimal('2.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-1.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__radians__gt=0)
            self.assertQuerysetEqual(objs, [2.0], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Radians)
