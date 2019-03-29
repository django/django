import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Cosh
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class CoshTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_cosh=Cosh('normal')).first()
        self.assertIsNone(obj.null_cosh)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_cosh=Cosh('n1'), n2_cosh=Cosh('n2')).first()
        self.assertIsInstance(obj.n1_cosh, Decimal)
        self.assertIsInstance(obj.n2_cosh, Decimal)
        self.assertAlmostEqual(obj.n1_cosh, Decimal(math.cosh(obj.n1)))
        self.assertAlmostEqual(obj.n2_cosh, Decimal(math.cosh(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-17.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_cosh=Cosh('f1'), f2_cosh=Cosh('f2')).first()
        self.assertIsInstance(obj.f1_cosh, float)
        self.assertIsInstance(obj.f2_cosh, float)
        self.assertAlmostEqual(obj.f1_cosh, math.cosh(obj.f1))
        self.assertAlmostEqual(obj.f2_cosh, math.cosh(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-10, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_cosh=Cosh('small'),
            normal_cosh=Cosh('normal'),
            big_cosh=Cosh('big'),
        ).first()
        self.assertIsInstance(obj.small_cosh, float)
        self.assertIsInstance(obj.normal_cosh, float)
        self.assertIsInstance(obj.big_cosh, float)
        self.assertAlmostEqual(obj.small_cosh, math.cosh(obj.small))
        self.assertAlmostEqual(obj.normal_cosh, math.cosh(obj.normal))
        self.assertAlmostEqual(obj.big_cosh, math.cosh(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Cosh):
            DecimalModel.objects.create(n1=Decimal('-8.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('3.14'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__cosh__lt=100).get()
            self.assertEqual(obj.n1, Decimal('3.14'))
