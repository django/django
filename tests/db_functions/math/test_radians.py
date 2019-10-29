import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Radians
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class RadiansTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_radians=Radians('normal')).first()
        self.assertIsNone(obj.null_radians)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_radians=Radians('n1'), n2_radians=Radians('n2')).first()
        self.assertIsInstance(obj.n1_radians, Decimal)
        self.assertIsInstance(obj.n2_radians, Decimal)
        self.assertAlmostEqual(obj.n1_radians, Decimal(math.radians(obj.n1)))
        self.assertAlmostEqual(obj.n2_radians, Decimal(math.radians(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_radians=Radians('f1'), f2_radians=Radians('f2')).first()
        self.assertIsInstance(obj.f1_radians, float)
        self.assertIsInstance(obj.f2_radians, float)
        self.assertAlmostEqual(obj.f1_radians, math.radians(obj.f1))
        self.assertAlmostEqual(obj.f2_radians, math.radians(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_radians=Radians('small'),
            normal_radians=Radians('normal'),
            big_radians=Radians('big'),
        ).first()
        self.assertIsInstance(obj.small_radians, float)
        self.assertIsInstance(obj.normal_radians, float)
        self.assertIsInstance(obj.big_radians, float)
        self.assertAlmostEqual(obj.small_radians, math.radians(obj.small))
        self.assertAlmostEqual(obj.normal_radians, math.radians(obj.normal))
        self.assertAlmostEqual(obj.big_radians, math.radians(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Radians):
            DecimalModel.objects.create(n1=Decimal('2.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-1.0'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__radians__gt=0).get()
            self.assertEqual(obj.n1, Decimal('2.0'))
