import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Tan
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class TanTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Tan('n1'), n2_d=Tan('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.tan(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.tan(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Tan('f1'), f2_d=Tan('f2')).first()
        self.assertAlmostEqual(float(obj.f1_d), math.tan(obj.f1))
        self.assertAlmostEqual(float(obj.f2_d), math.tan(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_d=Tan('small'),
            normal_d=Tan('normal'),
            big_d=Tan('big'),
        ).first()
        self.assertAlmostEqual(obj.small_d, math.tan(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.tan(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.tan(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Tan)
            DecimalModel.objects.create(n1=Decimal('0.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('12.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__tan__lt=0)
            self.assertQuerysetEqual(objs, [12.0], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Tan)
