import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import Sqrt
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class SqrtTests(TestCase):
    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_sqrt=Sqrt("normal")).first()
        self.assertIsNone(obj.null_sqrt)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal("12.9"), n2=Decimal("0.6"))
        obj = DecimalModel.objects.annotate(
            n1_sqrt=Sqrt("n1"), n2_sqrt=Sqrt("n2")
        ).first()
        self.assertIsInstance(obj.n1_sqrt, Decimal)
        self.assertIsInstance(obj.n2_sqrt, Decimal)
        self.assertAlmostEqual(obj.n1_sqrt, Decimal(math.sqrt(obj.n1)))
        self.assertAlmostEqual(obj.n2_sqrt, Decimal(math.sqrt(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=27.5, f2=0.33)
        obj = FloatModel.objects.annotate(
            f1_sqrt=Sqrt("f1"), f2_sqrt=Sqrt("f2")
        ).first()
        self.assertIsInstance(obj.f1_sqrt, float)
        self.assertIsInstance(obj.f2_sqrt, float)
        self.assertAlmostEqual(obj.f1_sqrt, math.sqrt(obj.f1))
        self.assertAlmostEqual(obj.f2_sqrt, math.sqrt(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(small=20, normal=15, big=1)
        obj = IntegerModel.objects.annotate(
            small_sqrt=Sqrt("small"),
            normal_sqrt=Sqrt("normal"),
            big_sqrt=Sqrt("big"),
        ).first()
        self.assertIsInstance(obj.small_sqrt, float)
        self.assertIsInstance(obj.normal_sqrt, float)
        self.assertIsInstance(obj.big_sqrt, float)
        self.assertAlmostEqual(obj.small_sqrt, math.sqrt(obj.small))
        self.assertAlmostEqual(obj.normal_sqrt, math.sqrt(obj.normal))
        self.assertAlmostEqual(obj.big_sqrt, math.sqrt(obj.big))

    def test_transform(self):
        with register_lookup(DecimalField, Sqrt):
            DecimalModel.objects.create(n1=Decimal("6.0"), n2=Decimal("0"))
            DecimalModel.objects.create(n1=Decimal("1.0"), n2=Decimal("0"))
            obj = DecimalModel.objects.filter(n1__sqrt__gt=2).get()
            self.assertEqual(obj.n1, Decimal("6.0"))
