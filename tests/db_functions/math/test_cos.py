import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Cos
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class CosTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_cos=Cos('n1'), n2_cos=Cos('n2')).first()
        self.assertAlmostEqual(obj.n1_cos, math.cos(obj.n1))
        self.assertAlmostEqual(obj.n2_cos, math.cos(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_cos=Cos('f1'), f2_cos=Cos('f2')).first()
        self.assertAlmostEqual(obj.f1_cos, math.cos(obj.f1))
        self.assertAlmostEqual(obj.f2_cos, math.cos(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_cos=Cos('small'),
            normal_cos=Cos('normal'),
            big_cos=Cos('big')).first()
        self.assertAlmostEqual(float(obj.small_cos), math.cos(obj.small))
        self.assertAlmostEqual(float(obj.normal_cos), math.cos(obj.normal))
        self.assertAlmostEqual(float(obj.big_cos), math.cos(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Cos, 'cos')
            DecimalModel.objects.create(n1=Decimal('-8.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('3.14'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__cos__gt=-0.2)
            self.assertQuerysetEqual(objs, [-8.0], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Cos, 'cos')
