import math
from decimal import Decimal

from django.db.models.functions import Log2
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class Log2Tests(TestCase):

    def test_null(self):
        IntegerModel.objects.create(big=100)
        obj = IntegerModel.objects.annotate(
            null_log2_small=Log2('small'),
            null_log2_normal=Log2('normal'),
        ).first()
        self.assertIsNone(obj.null_log2_small)
        self.assertIsNone(obj.null_log2_normal)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('3.6'))
        obj = DecimalModel.objects.annotate(n_log2=Log2('n1')).first()
        self.assertIsInstance(obj.n_log2, Decimal)
        self.assertAlmostEqual(obj.n_log2, Decimal(math.log2(obj.n1)))

    def test_float(self):
        FloatModel.objects.create(f1=2.0, f2=4.0)
        obj = FloatModel.objects.annotate(f_log2=Log2('f1')).first()
        self.assertIsInstance(obj.f_log2, float)
        self.assertAlmostEqual(obj.f_log2, math.log2(obj.f1))

    def test_integer(self):
        IntegerModel.objects.create(small=4, normal=8, big=2)
        obj = IntegerModel.objects.annotate(
            small_log2=Log2('small'),
            normal_log2=Log2('normal'),
            big_log2=Log2('big'),
        ).first()
        self.assertIsInstance(obj.small_log2, float)
        self.assertIsInstance(obj.normal_log2, float)
        self.assertIsInstance(obj.big_log2, float)
        self.assertAlmostEqual(obj.small_log2, math.log2(obj.small))
        self.assertAlmostEqual(obj.normal_log2, math.log2(obj.normal))
        self.assertAlmostEqual(obj.big_log2, math.log2(obj.big))
