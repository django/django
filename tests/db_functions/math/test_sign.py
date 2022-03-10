from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Sign
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class SignTests(TestCase):
    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_sign=Sign("normal")).first()
        self.assertIsNone(obj.null_sign)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal("-12.9"), n2=Decimal("0.6"))
        obj = DecimalModel.objects.annotate(
            n1_sign=Sign("n1"), n2_sign=Sign("n2")
        ).first()
        self.assertIsInstance(obj.n1_sign, Decimal)
        self.assertIsInstance(obj.n2_sign, Decimal)
        self.assertEqual(obj.n1_sign, Decimal("-1"))
        self.assertEqual(obj.n2_sign, Decimal("1"))

    def test_float(self):
        FloatModel.objects.create(f1=-27.5, f2=0.33)
        obj = FloatModel.objects.annotate(
            f1_sign=Sign("f1"), f2_sign=Sign("f2")
        ).first()
        self.assertIsInstance(obj.f1_sign, float)
        self.assertIsInstance(obj.f2_sign, float)
        self.assertEqual(obj.f1_sign, -1.0)
        self.assertEqual(obj.f2_sign, 1.0)

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=0, big=20)
        obj = IntegerModel.objects.annotate(
            small_sign=Sign("small"),
            normal_sign=Sign("normal"),
            big_sign=Sign("big"),
        ).first()
        self.assertIsInstance(obj.small_sign, int)
        self.assertIsInstance(obj.normal_sign, int)
        self.assertIsInstance(obj.big_sign, int)
        self.assertEqual(obj.small_sign, -1)
        self.assertEqual(obj.normal_sign, 0)
        self.assertEqual(obj.big_sign, 1)

    def test_transform(self):
        with register_lookup(DecimalField, Sign):
            DecimalModel.objects.create(n1=Decimal("5.4"), n2=Decimal("0"))
            DecimalModel.objects.create(n1=Decimal("-0.1"), n2=Decimal("0"))
            obj = DecimalModel.objects.filter(n1__sign__lt=0, n2__sign=0).get()
            self.assertEqual(obj.n1, Decimal("-0.1"))
