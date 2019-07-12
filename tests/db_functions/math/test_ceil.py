import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Ceil
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class CeilTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_ceil=Ceil('normal')).first()
        self.assertIsNone(obj.null_ceil)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_ceil=Ceil('n1'), n2_ceil=Ceil('n2')).first()
        self.assertIsInstance(obj.n1_ceil, Decimal)
        self.assertIsInstance(obj.n2_ceil, Decimal)
        self.assertEqual(obj.n1_ceil, Decimal(math.ceil(obj.n1)))
        self.assertEqual(obj.n2_ceil, Decimal(math.ceil(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-12.5, f2=21.33)
        obj = FloatModel.objects.annotate(f1_ceil=Ceil('f1'), f2_ceil=Ceil('f2')).first()
        self.assertIsInstance(obj.f1_ceil, float)
        self.assertIsInstance(obj.f2_ceil, float)
        self.assertEqual(obj.f1_ceil, math.ceil(obj.f1))
        self.assertEqual(obj.f2_ceil, math.ceil(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-11, normal=0, big=-100)
        obj = IntegerModel.objects.annotate(
            small_ceil=Ceil('small'),
            normal_ceil=Ceil('normal'),
            big_ceil=Ceil('big'),
        ).first()
        self.assertIsInstance(obj.small_ceil, int)
        self.assertIsInstance(obj.normal_ceil, int)
        self.assertIsInstance(obj.big_ceil, int)
        self.assertEqual(obj.small_ceil, math.ceil(obj.small))
        self.assertEqual(obj.normal_ceil, math.ceil(obj.normal))
        self.assertEqual(obj.big_ceil, math.ceil(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Ceil):
            DecimalModel.objects.create(n1=Decimal('3.12'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('1.25'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__ceil__gt=3).get()
            self.assertEqual(obj.n1, Decimal('3.12'))
