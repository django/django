import math
from decimal import Decimal

from django.db.models.functions import ATan2
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class ATan2Tests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-9.9'), n2=Decimal('4.6'))
        obj = DecimalModel.objects.annotate(atan2=ATan2('n1', 'n2')).first()
        self.assertAlmostEqual(obj.atan2, Decimal(math.atan2(obj.n1, obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-25, f2=0.33)
        obj = FloatModel.objects.annotate(atan2=ATan2('f1', 'f2')).first()
        self.assertAlmostEqual(obj.atan2, math.atan2(obj.f1, obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=0, normal=1, big=10)
        obj = IntegerModel.objects.annotate(
            atan2_sn=ATan2('small', 'normal'),
            atan2_nb=ATan2('normal', 'big'),
        ).first()
        self.assertAlmostEqual(obj.atan2_sn, math.atan2(obj.small, obj.normal))
        self.assertAlmostEqual(obj.atan2_nb, math.atan2(obj.normal, obj.big))
