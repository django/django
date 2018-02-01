import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Ceil
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class CeilTests(TestCase):

    def test_float(self):
        FloatModel.objects.create(f1=-12.5, f2=21.33)
        obj = FloatModel.objects.annotate(f1_ceil=Ceil('f1'), f2_ceil=Ceil('f2')).first()
        self.assertAlmostEqual(int(obj.f1_ceil), int(math.ceil(obj.f1)))
        self.assertAlmostEqual(int(obj.f2_ceil), int(math.ceil(obj.f2)))

    def test_integer(self):
        IntegerModel.objects.create(small=-11, normal=0, big=-100)
        obj = IntegerModel.objects.annotate(
            small_ceil=Ceil('small'),
            normal_ceil=Ceil('normal'),
            big_ceil=Ceil('big')).first()
        self.assertEqual(obj.small_ceil, math.ceil(obj.small))
        self.assertEqual(obj.normal_ceil, math.ceil(obj.normal))
        self.assertEqual(obj.big_ceil, math.ceil(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Ceil, 'ceil')
            DecimalModel.objects.create(n1=Decimal('3.12'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('1.25'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__ceil__gt=3)
            self.assertQuerysetEqual(objs, [float(3.12)], lambda a: float(a.n1))
        finally:
            DecimalField._unregister_lookup(Ceil, 'ceil')
