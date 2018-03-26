import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Tan
from django.test import TestCase

from ..models import DecimalModel, FloatModel, IntegerModel


class TanTests(TestCase):

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-12.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_tan=Tan('n1'), n2_tan=Tan('n2')).first()
        self.assertIsInstance(obj.n1_tan, Decimal)
        self.assertIsInstance(obj.n2_tan, Decimal)
        self.assertAlmostEqual(obj.n1_tan, Decimal(math.tan(obj.n1)))
        self.assertAlmostEqual(obj.n2_tan, Decimal(math.tan(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_tan=Tan('f1'), f2_tan=Tan('f2')).first()
        self.assertIsInstance(obj.f1_tan, float)
        self.assertIsInstance(obj.f2_tan, float)
        self.assertAlmostEqual(obj.f1_tan, math.tan(obj.f1))
        self.assertAlmostEqual(obj.f2_tan, math.tan(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_tan=Tan('small'),
            normal_tan=Tan('normal'),
            big_tan=Tan('big'),
        ).first()
        self.assertIsInstance(obj.small_tan, float)
        self.assertIsInstance(obj.normal_tan, float)
        self.assertIsInstance(obj.big_tan, float)
        self.assertAlmostEqual(obj.small_tan, math.tan(obj.small))
        self.assertAlmostEqual(obj.normal_tan, math.tan(obj.normal))
        self.assertAlmostEqual(obj.big_tan, math.tan(obj.big))

    def test_transform(self):
        try:
            DecimalField.register_lookup(Tan)
            DecimalModel.objects.create(n1=Decimal('0.0'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('12.0'), n2=Decimal('0'))
            objs = DecimalModel.objects.filter(n1__tan__lt=0)
            self.assertQuerysetEqual(objs, [Decimal('12.0')], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Tan)
