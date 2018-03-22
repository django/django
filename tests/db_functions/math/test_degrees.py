import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Degrees
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class DegreesTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Degrees('n1'), n2_d=Degrees('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.degrees(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.degrees(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Degrees('f1'), f2_d=Degrees('f2')).first()
        self.assertAlmostEqual(obj.f1_d, math.degrees(obj.f1))
        self.assertAlmostEqual(obj.f2_d, math.degrees(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_d=Degrees('small'),
            normal_d=Degrees('normal'),
            big_d=Degrees('big'),
        ).first()
        self.assertAlmostEqual(obj.small_d, math.degrees(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.degrees(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.degrees(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Degrees)
            DecimalModel.objects.create(n1=Decimal('5.4'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-30'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__degrees__gt=0)
            self.assertQuerysetEqual(objs, [Decimal('5.4')], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Degrees)
