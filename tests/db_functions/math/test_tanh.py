import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Tanh
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class TanhTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_tanh=Tanh('normal')).first()
        self.assertIsNone(obj.null_tanh)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_tanh=Tanh('n1'), n2_tanh=Tanh('n2')).first()
        self.assertIsInstance(obj.n1_tanh, Decimal)
        self.assertIsInstance(obj.n2_tanh, Decimal)
        self.assertAlmostEqual(obj.n1_tanh, Decimal(math.tanh(obj.n1)))
        self.assertAlmostEqual(obj.n2_tanh, Decimal(math.tanh(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_tanh=Tanh('f1'), f2_tanh=Tanh('f2')).first()
        self.assertIsInstance(obj.f1_tanh, float)
        self.assertIsInstance(obj.f2_tanh, float)
        self.assertAlmostEqual(obj.f1_tanh, math.tanh(obj.f1))
        self.assertAlmostEqual(obj.f2_tanh, math.tanh(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_tanh=Tanh('small'),
            normal_tanh=Tanh('normal'),
            big_tanh=Tanh('big'),
        ).first()
        self.assertIsInstance(obj.small_tanh, float)
        self.assertIsInstance(obj.normal_tanh, float)
        self.assertIsInstance(obj.big_tanh, float)
        self.assertAlmostEqual(obj.small_tanh, math.tanh(obj.small))
        self.assertAlmostEqual(obj.normal_tanh, math.tanh(obj.normal))
        self.assertAlmostEqual(obj.big_tanh, math.tanh(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Tanh):
            DecimalModel.objects.create(n1=Decimal('-9.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('12.0'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__tanh__lt=0).get()
            self.assertEqual(obj.n1, Decimal('-9.0'))
