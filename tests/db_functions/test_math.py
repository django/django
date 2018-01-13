from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Abs
from django.test import TestCase

from .models import DecimalModel, FloatModel, IntegerModel


class MathFunctionTests(TestCase):
    def test_abs_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-1.1'), n2=Decimal('1.2'))
        obj = DecimalModel.objects.annotate(
            n1_abs=Abs('n1'),
            n2_abs=Abs('n2')).first()

        self.assertEqual(obj.n1_abs, -obj.n1)
        self.assertEqual(obj.n2_abs, obj.n2)

    def test_abs_integer(self):
        IntegerModel.objects.create(small=-1, normal=-2, big=-3)
        obj = IntegerModel.objects.annotate(
            small_abs=Abs('small'),
            normal_abs=Abs('normal'),
            big_abs=Abs('big'),).first()

        self.assertEqual(obj.small_abs, -obj.small)
        self.assertEqual(obj.normal_abs, -obj.normal)
        self.assertEqual(obj.big_abs, -obj.big)

    def test_abs_float(self):
        FloatModel.objects.create(f1=-1.5, f2=1.2)
        obj = FloatModel.objects.annotate(
            f1_abs=Abs('f1'),
            f2_abs=Abs('f2')).first()

        self.assertEqual(obj.f1_abs, -obj.f1)
        self.assertEqual(obj.f2_abs, obj.f2)

    def test_abs_ordering(self):
        DecimalModel.objects.create(n1=Decimal('-1.5'), n2=Decimal('0'))
        DecimalModel.objects.create(n1=Decimal('0'), n2=Decimal('0'))
        DecimalModel.objects.create(n1=Decimal('0.5'), n2=Decimal('0'))
        DecimalModel.objects.create(n1=Decimal('2'), n2=Decimal('0'))

        objs = DecimalModel.objects.order_by(Abs('n1'))

        self.assertQuerysetEqual(objs, [0, 0.5, -1.5, 2], lambda a: a.n1)

    def test_abs_transform(self):
        try:
            DecimalField.register_lookup(Abs, 'abs')

            DecimalModel.objects.create(n1=Decimal('-1.5'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-0.5'), n2=Decimal('0'))

            objs = DecimalModel.objects.filter(n1__abs__gt=1)
            self.assertQuerysetEqual(objs, [-1.5], lambda a: a.n1)
        finally:
            DecimalField._unregister_lookup(Abs, 'abs')
