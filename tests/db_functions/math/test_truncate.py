import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Truncate
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class TruncateTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_truncate=Truncate('normal')).first()
        self.assertIsNone(obj.null_truncate)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_truncate=Truncate('n1'), n2_truncate=Truncate('n2')).first()
        self.assertIsInstance(obj.n1_truncate, Decimal)
        self.assertIsInstance(obj.n2_truncate, Decimal)
        self.assertAlmostEqual(obj.n1_truncate, math.trunc(obj.n1))
        self.assertAlmostEqual(obj.n2_truncate, math.trunc(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.55, f2=0.55)
        obj = FloatModel.objects.annotate(f1_truncate=Truncate('f1'), f2_truncate=Truncate('f2')).first()
        self.assertIsInstance(obj.f1_truncate, float)
        self.assertIsInstance(obj.f2_truncate, float)
        self.assertAlmostEqual(obj.f1_truncate, math.trunc(obj.f1))
        self.assertAlmostEqual(obj.f2_truncate, math.trunc(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_truncate=Truncate('small'),
            normal_truncate=Truncate('normal'),
            big_truncate=Truncate('big'),
        ).first()
        self.assertIsInstance(obj.small_truncate, int)
        self.assertIsInstance(obj.normal_truncate, int)
        self.assertIsInstance(obj.big_truncate, int)
        self.assertEqual(obj.small_truncate, math.trunc(obj.small))
        self.assertEqual(obj.normal_truncate, math.trunc(obj.normal))
        self.assertEqual(obj.big_truncate, math.trunc(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Truncate):
            DecimalModel.objects.create(n1=Decimal('2.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-1.0'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__truncate__gt=0).get()
            self.assertEqual(obj.n1, Decimal('2.0'))
