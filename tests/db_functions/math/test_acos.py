import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import ACos
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class ACosTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_acos=ACos('normal')).first()
        self.assertIsNone(obj.null_acos)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-0.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_acos=ACos('n1'), n2_acos=ACos('n2')).first()
        self.assertIsInstance(obj.n1_acos, Decimal)
        self.assertIsInstance(obj.n2_acos, Decimal)
        self.assertAlmostEqual(obj.n1_acos, Decimal(math.acos(obj.n1)))
        self.assertAlmostEqual(obj.n2_acos, Decimal(math.acos(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-0.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_acos=ACos('f1'), f2_acos=ACos('f2')).first()
        self.assertIsInstance(obj.f1_acos, float)
        self.assertIsInstance(obj.f2_acos, float)
        self.assertAlmostEqual(obj.f1_acos, math.acos(obj.f1))
        self.assertAlmostEqual(obj.f2_acos, math.acos(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=0, normal=1, big=-1)
        obj = IntegerModel.objects.annotate(
            small_acos=ACos('small'),
            normal_acos=ACos('normal'),
            big_acos=ACos('big'),
        ).first()
        self.assertIsInstance(obj.small_acos, float)
        self.assertIsInstance(obj.normal_acos, float)
        self.assertIsInstance(obj.big_acos, float)
        self.assertAlmostEqual(obj.small_acos, math.acos(obj.small))
        self.assertAlmostEqual(obj.normal_acos, math.acos(obj.normal))
        self.assertAlmostEqual(obj.big_acos, math.acos(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, ACos):
            DecimalModel.objects.create(n1=Decimal('0.5'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-0.9'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__acos__lt=2).get()
            self.assertEqual(obj.n1, Decimal('0.5'))
