import math
from decimal import Decimal

from django.db.models.functions import Log10
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class Log10Tests(TestCase):

    def test_null(self):
        IntegerModel.objects.create(big=100)
        obj = IntegerModel.objects.annotate(
            null_log10_small=Log10('small'),
            null_log10_normal=Log10('normal'),
        ).first()
        self.assertIsNone(obj.null_log10_small)
        self.assertIsNone(obj.null_log10_normal)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('3.6'))
        obj = DecimalModel.objects.annotate(n_log10=Log10('n1')).first()
        self.assertIsInstance(obj.n_log10, Decimal)
        self.assertAlmostEqual(obj.n_log10, Decimal(math.log10(obj.n1)))

    def test_float(self):
        FloatModel.objects.create(f1=2.0, f2=4.0)
        obj = FloatModel.objects.annotate(f_log10=Log10('f1')).first()
        self.assertIsInstance(obj.f_log10, float)
        self.assertAlmostEqual(obj.f_log10, math.log10(obj.f1))

    def test_integer(self):
        IntegerModel.objects.create(small=4, normal=8, big=2)
        obj = IntegerModel.objects.annotate(
            small_log10=Log10('small'),
            normal_log10=Log10('normal'),
            big_log10=Log10('big'),
        ).first()
        self.assertIsInstance(obj.small_log10, float)
        self.assertIsInstance(obj.normal_log10, float)
        self.assertIsInstance(obj.big_log10, float)
        self.assertAlmostEqual(obj.small_log10, math.log10(obj.small))
        self.assertAlmostEqual(obj.normal_log10, math.log10(obj.normal))
        self.assertAlmostEqual(obj.big_log10, math.log10(obj.big))
