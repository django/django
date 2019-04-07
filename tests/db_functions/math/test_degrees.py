import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Degrees
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class DegreesTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_degrees=Degrees('normal')).first()
        self.assertIsNone(obj.null_degrees)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_degrees=Degrees('n1'), n2_degrees=Degrees('n2')).first()
        self.assertIsInstance(obj.n1_degrees, Decimal)
        self.assertIsInstance(obj.n2_degrees, Decimal)
        self.assertAlmostEqual(obj.n1_degrees, Decimal(math.degrees(obj.n1)))
        self.assertAlmostEqual(obj.n2_degrees, Decimal(math.degrees(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_degrees=Degrees('f1'), f2_degrees=Degrees('f2')).first()
        self.assertIsInstance(obj.f1_degrees, float)
        self.assertIsInstance(obj.f2_degrees, float)
        self.assertAlmostEqual(obj.f1_degrees, math.degrees(obj.f1))
        self.assertAlmostEqual(obj.f2_degrees, math.degrees(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_degrees=Degrees('small'),
            normal_degrees=Degrees('normal'),
            big_degrees=Degrees('big'),
        ).first()
        self.assertIsInstance(obj.small_degrees, float)
        self.assertIsInstance(obj.normal_degrees, float)
        self.assertIsInstance(obj.big_degrees, float)
        self.assertAlmostEqual(obj.small_degrees, math.degrees(obj.small))
        self.assertAlmostEqual(obj.normal_degrees, math.degrees(obj.normal))
        self.assertAlmostEqual(obj.big_degrees, math.degrees(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Degrees):
            DecimalModel.objects.create(n1=Decimal('5.4'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-30'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__degrees__gt=0).get()
            self.assertEqual(obj.n1, Decimal('5.4'))
