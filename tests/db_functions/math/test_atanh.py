import math
from decimal import Decimal

from django.db.models import DecimalField
from django.db.models.functions import ATanh
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import DecimalModel, FloatModel, IntegerModel


class ATanhTests(TestCase):

    def test_null(self):
        IntegerModel.objects.create()
        obj = IntegerModel.objects.annotate(null_atanh=ATanh('normal')).first()
        self.assertIsNone(obj.null_atanh)

    def test_decimal(self):
        DecimalModel.objects.create(n1=Decimal('-0.9'), n2=Decimal('0.6'))
        obj = DecimalModel.objects.annotate(n1_atanh=ATanh('n1'), n2_atanh=ATanh('n2')).first()
        self.assertIsInstance(obj.n1_atanh, Decimal)
        self.assertIsInstance(obj.n2_atanh, Decimal)
        self.assertAlmostEqual(obj.n1_atanh, Decimal(math.atanh(obj.n1)))
        self.assertAlmostEqual(obj.n2_atanh, Decimal(math.atanh(obj.n2)))

    def test_float(self):
        FloatModel.objects.create(f1=-0.5, f2=0.33)
        obj = FloatModel.objects.annotate(f1_atanh=ATanh('f1'), f2_atanh=ATanh('f2')).first()
        self.assertIsInstance(obj.f1_atanh, float)
        self.assertIsInstance(obj.f2_atanh, float)
        self.assertAlmostEqual(obj.f1_atanh, math.atanh(obj.f1))
        self.assertAlmostEqual(obj.f2_atanh, math.atanh(obj.f2))

    def test_integer(self):
        IntegerModel.objects.create(normal=0)
        obj = IntegerModel.objects.annotate(normal_atanh=ATanh('normal')).first()
        self.assertIsInstance(obj.normal_atanh, float)
        self.assertAlmostEqual(obj.normal_atanh, math.atanh(obj.normal))

    def test_transform(self):
        with register_lookup(DecimalField, ATanh):
            DecimalModel.objects.create(n1=Decimal('0.9'), n2=Decimal('0'))
            DecimalModel.objects.create(n1=Decimal('-0.9'), n2=Decimal('0'))
            obj = DecimalModel.objects.filter(n1__atanh__gt=0).get()
            self.assertEqual(obj.n1, Decimal('0.9'))
