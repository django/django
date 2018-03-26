from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Round
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class RoundTests(TestCase):

    def assertRoundEqual(self, num1, num2):
        if num1 - num2 == 1:
            self.assertAlmostEqual(num1-1, num2)
        elif num1 - num2 == -1:
            self.assertAlmostEqual(num1+1, num2)
        else:
            self.assertAlmostEqual(num1, num2)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_round=Round('n1'), n2_round=Round('n2')).first()
        self.assertIsInstance(obj.n1_round, Decimal)
        self.assertIsInstance(obj.n2_round, Decimal)
        self.assertRoundEqual(obj.n1_round, round(obj.n1))
        self.assertRoundEqual(obj.n2_round, round(obj.n2))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.5)
        obj = FloatModel.objects.annotate(f1_round=Round('f1'), f2_round=Round('f2')).first()
        self.assertIsInstance(obj.f1_round, float)
        self.assertIsInstance(obj.f2_round, float)
        self.assertRoundEqual(obj.f1_round, round(obj.f1))
        self.assertRoundEqual(obj.f2_round, round(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_round=Round('small'),
            normal_round=Round('normal'),
            big_round=Round('big'),
        ).first()
        self.assertIsInstance(obj.small_round, int)
        self.assertIsInstance(obj.normal_round, int)
        self.assertIsInstance(obj.big_round, int)
        self.assertAlmostEqual(obj.small_round, round(obj.small))
        self.assertAlmostEqual(obj.normal_round, round(obj.normal))
        self.assertAlmostEqual(obj.big_round, round(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Round)
            DecimalModel.objects.create(n1=Decimal('2.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-1.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__round__gt=0)
            self.assertQuerysetEqual(objs, [Decimal('2.0')], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Round)
