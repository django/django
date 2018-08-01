import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Exp
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class ExpTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_exp=Exp('n1'), n2_exp=Exp('n2')).first()
        self.assertIsInstance(obj.n1_exp, Decimal)
        self.assertIsInstance(obj.n2_exp, Decimal)
        self.assertAlmostEqual(obj.n1_exp, Decimal(math.exp(obj.n1)))
        self.assertAlmostEqual(obj.n2_exp, Decimal(math.exp(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_exp=Exp('f1'), f2_exp=Exp('f2')).first()
        self.assertIsInstance(obj.f1_exp, float)
        self.assertIsInstance(obj.f2_exp, float)
        self.assertAlmostEqual(obj.f1_exp, math.exp(obj.f1))
        self.assertAlmostEqual(obj.f2_exp, math.exp(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_exp=Exp('small'),
            normal_exp=Exp('normal'),
            big_exp=Exp('big'),
        ).first()
        self.assertIsInstance(obj.small_exp, float)
        self.assertIsInstance(obj.normal_exp, float)
        self.assertIsInstance(obj.big_exp, float)
        self.assertAlmostEqual(obj.small_exp, math.exp(obj.small))
        self.assertAlmostEqual(obj.normal_exp, math.exp(obj.normal))
        self.assertAlmostEqual(obj.big_exp, math.exp(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Exp)
            DecimalModel.objects.create(n1=Decimal('12.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-1.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__exp__gt=10)
            self.assertQuerysetEqual(objs, [Decimal('12.0')], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Exp)
