import unittest
from decimal import Decimal

from django.db import connection
from django.db.models import DecimalField
from django.db.models.functions import Pi, Round
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class RoundTests(TestCase):
    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_round=Round("normal")).first()
        self.assertIsNone(obj.null_round)

    def test_null_with_precision(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_round=Round("normal", 5)).first()
        self.assertIsNone(obj.null_round)

    def test_null_with_negative_precision(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_round=Round("normal", -1)).first()
        self.assertIsNone(obj.null_round)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal("-12.9"), n2=Decimal("0.6"))
        obj = DecimalModel.objects.annotate(
            n1_round=Round("n1"), n2_round=Round("n2")
        ).first()
        self.assertIsInstance(obj.n1_round, Decimal)
        self.assertIsInstance(obj.n2_round, Decimal)
        self.assertAlmostEqual(obj.n1_round, obj.n1, places=0)
        self.assertAlmostEqual(obj.n2_round, obj.n2, places=0)

    def test_decimal_with_precision(self):
        DecimalModel.objects.create(n1=Decimal("-5.75"), n2=Pi())
        obj = DecimalModel.objects.annotate(
            n1_round=Round("n1", 1),
            n2_round=Round("n2", 5),
        ).first()
        self.assertIsInstance(obj.n1_round, Decimal)
        self.assertIsInstance(obj.n2_round, Decimal)
        self.assertAlmostEqual(obj.n1_round, obj.n1, places=1)
        self.assertAlmostEqual(obj.n2_round, obj.n2, places=5)

    def test_decimal_with_negative_precision(self):
        DecimalModel.objects.create(n1=Decimal("365.25"))
        obj = DecimalModel.objects.annotate(n1_round=Round("n1", -1)).first()
        self.assertIsInstance(obj.n1_round, Decimal)
        self.assertEqual(obj.n1_round, 370)

    def test_float(self):
        FloatModel.objects.create(f1=-27.55, f2=0.55)
        obj = FloatModel.objects.annotate(
            f1_round=Round("f1"), f2_round=Round("f2")
        ).first()
        self.assertIsInstance(obj.f1_round, float)
        self.assertIsInstance(obj.f2_round, float)
        self.assertAlmostEqual(obj.f1_round, obj.f1, places=0)
        self.assertAlmostEqual(obj.f2_round, obj.f2, places=0)

    def test_float_with_precision(self):
        FloatModel.objects.create(f1=-5.75, f2=Pi())
        obj = FloatModel.objects.annotate(
            f1_round=Round("f1", 1),
            f2_round=Round("f2", 5),
        ).first()
        self.assertIsInstance(obj.f1_round, float)
        self.assertIsInstance(obj.f2_round, float)
        self.assertAlmostEqual(obj.f1_round, obj.f1, places=1)
        self.assertAlmostEqual(obj.f2_round, obj.f2, places=5)

    def test_float_with_negative_precision(self):
        FloatModel.objects.create(f1=365.25)
        obj = FloatModel.objects.annotate(f1_round=Round("f1", -1)).first()
        self.assertIsInstance(obj.f1_round, float)
        self.assertEqual(obj.f1_round, 370)

    def test_integer(self):
        IntegerModel.objects.create(small=-20, normal=15, big=-1)
        obj = IntegerModel.objects.annotate(
            small_round=Round("small"),
            normal_round=Round("normal"),
            big_round=Round("big"),
        ).first()
        self.assertIsInstance(obj.small_round, int)
        self.assertIsInstance(obj.normal_round, int)
        self.assertIsInstance(obj.big_round, int)
        self.assertAlmostEqual(obj.small_round, obj.small, places=0)
        self.assertAlmostEqual(obj.normal_round, obj.normal, places=0)
        self.assertAlmostEqual(obj.big_round, obj.big, places=0)

    def test_integer_with_precision(self):
        IntegerModel.objects.create(small=-5, normal=3, big=-100)
        obj = IntegerModel.objects.annotate(
            small_round=Round("small", 1),
            normal_round=Round("normal", 5),
            big_round=Round("big", 2),
        ).first()
        self.assertIsInstance(obj.small_round, int)
        self.assertIsInstance(obj.normal_round, int)
        self.assertIsInstance(obj.big_round, int)
        self.assertAlmostEqual(obj.small_round, obj.small, places=1)
        self.assertAlmostEqual(obj.normal_round, obj.normal, places=5)
        self.assertAlmostEqual(obj.big_round, obj.big, places=2)

    def test_integer_with_negative_precision(self):
        IntegerModel.objects.create(normal=365)
        obj = IntegerModel.objects.annotate(normal_round=Round("normal", -1)).first()
        self.assertIsInstance(obj.normal_round, int)
        expected = 360 if connection.features.rounds_to_even else 370
        self.assertEqual(obj.normal_round, expected)

    def test_transform(self):
        with register_lookup(DecimalField, Round):
            DecimalModel.objects.create(n1=Decimal("2.0"), n2=Decimal("0"))
            DecimalModel.objects.create(n1=Decimal("-1.0"), n2=Decimal("0"))
            obj = DecimalModel.objects.filter(n1__round__gt=0).get()
            self.assertEqual(obj.n1, Decimal("2.0"))

    @unittest.skipUnless(
        connection.vendor == "sqlite",
        "SQLite doesn't support negative precision.",
    )
    def test_unsupported_negative_precision(self):
        FloatModel.objects.create(f1=123.45)
        msg = "SQLite does not support negative precision."
        with self.assertRaisesMessage(ValueError, msg):
            FloatModel.objects.annotate(value=Round("f1", -1)).first()
