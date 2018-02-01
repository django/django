import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Floor
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class FloorTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Floor('n1'), n2_d=Floor('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.floor(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.floor(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Floor('f1'), f2_d=Floor('f2')).first()
        self.assertAlmostEqual(float(obj.f1_d), math.floor(obj.f1))
        self.assertAlmostEqual(float(obj.f2_d), math.floor(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_d=Floor('small'),
            normal_d=Floor('normal'),
            big_d=Floor('big')).first()
        self.assertAlmostEqual(obj.small_d, math.floor(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.floor(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.floor(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Floor, 'floor')
            DecimalModel.objects.create(n1=Decimal('5.4'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('3.4'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__floor__gt=4)
            self.assertQuerysetEqual(objs, [float(5.4)], lambda a: float(a.n1))
        finally:
            DecimalField._unregister_lookup(Floor, 'floor')
