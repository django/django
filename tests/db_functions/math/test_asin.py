import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import ASin
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class ASinTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_asin=ASin('normal')).first()
        self.assertIsNone(obj.null_asin)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('0.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_asin=ASin('n1'), n2_asin=ASin('n2')).first()
        self.assertIsInstance(obj.n1_asin, Decimal)
        self.assertIsInstance(obj.n2_asin, Decimal)
        self.assertAlmostEqual(obj.n1_asin, Decimal(math.asin(obj.n1)))
        self.assertAlmostEqual(obj.n2_asin, Decimal(math.asin(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-0.5, f2=0.87)
        obj = FloatModel.objects.annotate(f1_asin=ASin('f1'), f2_asin=ASin('f2')).first()
        self.assertIsInstance(obj.f1_asin, float)
        self.assertIsInstance(obj.f2_asin, float)
        self.assertAlmostEqual(obj.f1_asin, math.asin(obj.f1))
        self.assertAlmostEqual(obj.f2_asin, math.asin(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=0, normal=1, big=-1)
        obj = IntegerModel.objects.annotate(
            small_asin=ASin('small'),
            normal_asin=ASin('normal'),
            big_asin=ASin('big'),
        ).first()
        self.assertIsInstance(obj.small_asin, float)
        self.assertIsInstance(obj.normal_asin, float)
        self.assertIsInstance(obj.big_asin, float)
        self.assertAlmostEqual(obj.small_asin, math.asin(obj.small))
        self.assertAlmostEqual(obj.normal_asin, math.asin(obj.normal))
        self.assertAlmostEqual(obj.big_asin, math.asin(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, ASin):
            DecimalModel.objects.create(n1=Decimal('0.1'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('1.0'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__asin__gt=1).get()
            self.assertEqual(obj.n1, Decimal('1.0'))
