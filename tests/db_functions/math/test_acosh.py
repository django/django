import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import ACosh
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class ACoshTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_acosh=ACosh('normal')).first()
        self.assertIsNone(obj.null_acosh)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('2.3'), n2=Decimal('4.7'))
        obj = DecimalModel.objects.annotate(n1_acosh=ACosh('n1'), n2_acosh=ACosh('n2')).first()
        self.assertIsInstance(obj.n1_acosh, Decimal)
        self.assertIsInstance(obj.n2_acosh, Decimal)
        self.assertAlmostEqual(obj.n1_acosh, Decimal(math.acosh(obj.n1)))
        self.assertAlmostEqual(obj.n2_acosh, Decimal(math.acosh(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=4.1, f2=1.33)
        obj = FloatModel.objects.annotate(f1_acosh=ACosh('f1'), f2_acosh=ACosh('f2')).first()
        self.assertIsInstance(obj.f1_acosh, float)
        self.assertIsInstance(obj.f2_acosh, float)
        self.assertAlmostEqual(obj.f1_acosh, math.acosh(obj.f1))
        self.assertAlmostEqual(obj.f2_acosh, math.acosh(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=1, normal=3, big=5)
        obj = IntegerModel.objects.annotate(
            small_acosh=ACosh('small'),
            normal_acosh=ACosh('normal'),
            big_acosh=ACosh('big'),
        ).first()
        self.assertIsInstance(obj.small_acosh, float)
        self.assertIsInstance(obj.normal_acosh, float)
        self.assertIsInstance(obj.big_acosh, float)
        self.assertAlmostEqual(obj.small_acosh, math.acosh(obj.small))
        self.assertAlmostEqual(obj.normal_acosh, math.acosh(obj.normal))
        self.assertAlmostEqual(obj.big_acosh, math.acosh(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, ACosh):
            DecimalModel.objects.create(n1=Decimal('4.7'), n2=Decimal('1'))
            DecimalModel.objects.create(n1=Decimal('3.5'), n2=Decimal('1'))
            obj = DecimalModel.objects.filter(n1__acosh__lt=2).get()
            self.assertEqual(obj.n1, Decimal('3.5'))
