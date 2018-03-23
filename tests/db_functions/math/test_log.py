import math
from decimal import Decimal

from django.db.models.functions import Log
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class LogTests(TestCase):

    def assertLogEqual(self, n_log, n1, n2):
        log1 = math.log(n1, n2)
        log2 = math.log(n2, n1)
        if abs(n_log - log1) < abs(n_log - log2):
            self.assertAlmostEqual(n_log, log1)
        else:
            self.assertAlmostEqual(n_log, log2)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('3.6'))
        obj = DecimalModel.objects.annotate(n_log=Log('n1', 'n2')).first()
        self.assertLogEqual(obj.n_log, obj.n1, obj.n2)

    def test_float(self):
        FloatModel.objects.create(f1=27.5, f2=31.5)
        obj = FloatModel.objects.annotate(f_log=Log('f1', 'f2')).first()
        self.assertLogEqual(obj.f_log, obj.f1, obj.f2)

    def test_integer(self):
        IntegerModel.objects.create(small=4, normal=8, big=2)
        obj = IntegerModel.objects.annotate(
            small_log=Log('small', 'big'),
            normal_log=Log('normal', 'big'),
            big_log=Log('big', 'big'),
        ).first()
        self.assertLogEqual(obj.small_log, obj.small, obj.big)
        self.assertLogEqual(obj.normal_log, obj.normal, obj.big)
        self.assertLogEqual(obj.big_log, obj.big, obj.big)
