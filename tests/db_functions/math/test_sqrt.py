import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Sqrt
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class SqrtTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Sqrt('n1'), n2_d=Sqrt('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.sqrt(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.sqrt(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Sqrt('f1'), f2_d=Sqrt('f2')).first()
        self.assertAlmostEqual(float(obj.f1_d), math.sqrt(obj.f1))
        self.assertAlmostEqual(float(obj.f2_d), math.sqrt(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=20, normal=15, big=1)
        obj = IntegerModel.objects.annotate(
            small_d=Sqrt('small'),
            normal_d=Sqrt('normal'),
            big_d=Sqrt('big')).first()
        self.assertAlmostEqual(obj.small_d, math.sqrt(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.sqrt(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.sqrt(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Sqrt, 'sqrt')
            DecimalModel.objects.create(n1=Decimal('6.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('1.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__sqrt__gt=2)
            self.assertQuerysetEqual(objs, [6.0], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Sqrt, 'sqrt')
