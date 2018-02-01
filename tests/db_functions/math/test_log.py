import math
from decimal import Decimal

from django.db.models.functions import Log
from django.test import TestCase

from ..models import DecimalModel, IntegerModel


class LogTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('12.9'), n2=Decimal('3.6'))
        obj = DecimalModel.objects.annotate(n_log=Log('n1', 'n2')).first()
        self.assertTrue(
            float(obj.n_log) - math.log(obj.n2, obj.n1) < 0.01 or
            float(obj.n_log) - math.log(obj.n1, obj.n2) < 0.01)

    def test_integer(self):
        IntegerModel.objects.create(small=4, normal=8, big=2)
        obj = IntegerModel.objects.annotate(
            small_log=Log('small', 'big'),
            normal_log=Log('normal', 'big'),
            big_log=Log('big', 'big')).first()
        self.assertTrue(
            obj.small_log - math.log(obj.big, obj.small) < 0.01 or
            obj.small_log - math.log(obj.small, obj.big) < 0.01)
        self.assertTrue(
            obj.normal_log - math.log(obj.big, obj.normal) < 0.01 or
            obj.normal_log - math.log(obj.normal, obj.big) < 0.01)
        self.assertTrue(
            obj.big_log - math.log(obj.big, obj.big) < 0.01 or
            obj.normal_log - math.log(obj.normal, obj.big) < 0.01)
