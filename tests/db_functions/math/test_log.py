import math
from decimal import Decimal

from django.db.models.functions import Log
from django.test import TestCase

from ..models import DecimalModel, IntegerModel


class LogTests(TestCase):

    def assertLogEqual(self, n_log, n1, n2):
        diff1 = abs(float(n_log) - math.log(n2, n1))
        diff2 = abs(float(n_log) - math.log(n1, n2))
        if(diff1 < diff2):
            self.assertAlmostEqual(float(n_log), math.log(n2, n1), places=2)
        else:
            self.assertAlmostEqual(float(n_log), math.log(n1, n2), places=2)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('3.6'))
        obj = DecimalModel.objects.annotate(n_log=Log('n1', 'n2')).first()
        self.assertLogEqual(obj.n_log, obj.n1, obj.n2)

    def test_integer(self):
        IntegerModel.objects.create(small=4, normal=8, big=2)
        obj = IntegerModel.objects.annotate(
            small_log=Log('small', 'big'),
            normal_log=Log('normal', 'big'),
            big_log=Log('big', 'big'),
        ).first()
        self.assertLogEqual(obj.small_log, obj.big, obj.small)
        self.assertLogEqual(obj.normal_log, obj.big, obj.normal)
        self.assertLogEqual(obj.big_log, obj.big, obj.big)
