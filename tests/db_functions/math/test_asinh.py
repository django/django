import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import ASinh
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class ASinhTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_asinh=ASinh('normal')).first()
        self.assertIsNone(obj.null_asinh)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('0.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_asinh=ASinh('n1'), n2_asinh=ASinh('n2')).first()
        self.assertIsInstance(obj.n1_asinh, Decimal)
        self.assertIsInstance(obj.n2_asinh, Decimal)
        self.assertAlmostEqual(obj.n1_asinh, Decimal(math.asinh(obj.n1)))
        self.assertAlmostEqual(obj.n2_asinh, Decimal(math.asinh(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-0.5, f2=0.87)
        obj = FloatModel.objects.annotate(f1_asinh=ASinh('f1'), f2_asinh=ASinh('f2')).first()
        self.assertIsInstance(obj.f1_asinh, float)
        self.assertIsInstance(obj.f2_asinh, float)
        self.assertAlmostEqual(obj.f1_asinh, math.asinh(obj.f1))
        self.assertAlmostEqual(obj.f2_asinh, math.asinh(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=0, normal=1, big=-1)
        obj = IntegerModel.objects.annotate(
            small_asinh=ASinh('small'),
            normal_asinh=ASinh('normal'),
            big_asinh=ASinh('big'),
        ).first()
        self.assertIsInstance(obj.small_asinh, float)
        self.assertIsInstance(obj.normal_asinh, float)
        self.assertIsInstance(obj.big_asinh, float)
        self.assertAlmostEqual(obj.small_asinh, math.asinh(obj.small))
        self.assertAlmostEqual(obj.normal_asinh, math.asinh(obj.normal))
        self.assertAlmostEqual(obj.big_asinh, math.asinh(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, ASinh):
            DecimalModel.objects.create(n1=Decimal('0.1'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('1.2'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__asinh__gt=1).get()
            self.assertEqual(obj.n1, Decimal('1.2'))
