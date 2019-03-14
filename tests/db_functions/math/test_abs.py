from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Abs
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class AbsTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_abs=Abs('normal')).first()
        self.assertIsNone(obj.null_abs)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-0.8'), n2=Decimal('1.2'))
        obj = DecimalModel.objects.annotate(n1_abs=Abs('n1'), n2_abs=Abs('n2')).first()
        self.assertIsInstance(obj.n1_abs, Decimal)
        self.assertIsInstance(obj.n2_abs, Decimal)
        self.assertEqual(obj.n1, -obj.n1_abs)
        self.assertEqual(obj.n2, obj.n2_abs)

    def test_float(self):
        obj = FloatModel.objects.create(f1=-0.5, f2=12)
        obj = FloatModel.objects.annotate(f1_abs=Abs('f1'), f2_abs=Abs('f2')).first()
        self.assertIsInstance(obj.f1_abs, float)
        self.assertIsInstance(obj.f2_abs, float)
        self.assertEqual(obj.f1, -obj.f1_abs)
        self.assertEqual(obj.f2, obj.f2_abs)

    def test_integer(self):
        IntegerModel.objects.create(small=12, normal=0, big=-45)
        obj = IntegerModel.objects.annotate(
            small_abs=Abs('small'),
            normal_abs=Abs('normal'),
            big_abs=Abs('big'),
        ).first()
        self.assertIsInstance(obj.small_abs, int)
        self.assertIsInstance(obj.normal_abs, int)
        self.assertIsInstance(obj.big_abs, int)
        self.assertEqual(obj.small, obj.small_abs)
        self.assertEqual(obj.normal, obj.normal_abs)
        self.assertEqual(obj.big, -obj.big_abs)

    def test_transform(self):
        with register_lookup(DecimalField, Abs):
            DecimalModel.objects.create(n1=Decimal('-1.5'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-0.5'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__abs__gt=1).get()
            self.assertEqual(obj.n1, Decimal('-1.5'))
