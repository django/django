import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Exp
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class ExpTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_d=Exp('n1'), n2_d=Exp('n2')).first()
        self.assertAlmostEqual(obj.n1_d, math.exp(obj.n1))
        self.assertAlmostEqual(obj.n2_d, math.exp(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_d=Exp('f1'), f2_d=Exp('f2')).first()
        self.assertAlmostEqual(obj.f1_d, math.exp(obj.f1))
        self.assertAlmostEqual(obj.f2_d, math.exp(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_d=Exp('small'),
            normal_d=Exp('normal'),
            big_d=Exp('big'),
        ).first()
        self.assertAlmostEqual(obj.small_d, math.exp(obj.small))
        self.assertAlmostEqual(obj.normal_d, math.exp(obj.normal))
        self.assertAlmostEqual(obj.big_d, math.exp(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Exp)
            DecimalModel.objects.create(n1=Decimal('12.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-1.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__exp__gt=10)
            self.assertQuerysetEqual(objs, [12.0], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Exp)
