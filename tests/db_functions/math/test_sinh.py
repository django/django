import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Sinh
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class SinhTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_sinh=Sinh('normal')).first()
        self.assertIsNone(obj.null_sinh)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_sinh=Sinh('n1'), n2_sinh=Sinh('n2')).first()
        self.assertIsInstance(obj.n1_sinh, Decimal)
        self.assertIsInstance(obj.n2_sinh, Decimal)
        self.assertAlmostEqual(obj.n1_sinh, Decimal(math.sinh(obj.n1)))
        self.assertAlmostEqual(obj.n2_sinh, Decimal(math.sinh(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-17.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_sinh=Sinh('f1'), f2_sinh=Sinh('f2')).first()
        self.assertIsInstance(obj.f1_sinh, float)
        self.assertIsInstance(obj.f2_sinh, float)
        self.assertAlmostEqual(obj.f1_sinh, math.sinh(obj.f1))
        self.assertAlmostEqual(obj.f2_sinh, math.sinh(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-10, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_sinh=Sinh('small'),
            normal_sinh=Sinh('normal'),
            big_sinh=Sinh('big'),
        ).first()
        self.assertIsInstance(obj.small_sinh, float)
        self.assertIsInstance(obj.normal_sinh, float)
        self.assertIsInstance(obj.big_sinh, float)
        self.assertAlmostEqual(obj.small_sinh, math.sinh(obj.small))
        self.assertAlmostEqual(obj.normal_sinh, math.sinh(obj.normal))
        self.assertAlmostEqual(obj.big_sinh, math.sinh(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Sinh):
            DecimalModel.objects.create(n1=Decimal('5.4'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('0.1'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__sinh__lt=1).get()
            self.assertEqual(obj.n1, Decimal('0.1'))
