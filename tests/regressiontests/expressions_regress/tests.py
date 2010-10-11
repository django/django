"""
Spanning tests for all the operations that F() expressions can perform.
"""
from django.conf import settings
from django.db import models, DEFAULT_DB_ALIAS
from django.db.models import F
from django.test import TestCase, Approximate, skipUnlessDBFeature

from regressiontests.expressions_regress.models import Number


class ExpressionsRegressTests(TestCase):

    def setUp(self):
        Number(integer=-1).save()
        Number(integer=42).save()
        Number(integer=1337).save()
        self.assertEqual(Number.objects.update(float=F('integer')), 3)

    def test_fill_with_value_from_same_object(self):
        """
        We can fill a value in all objects with an other value of the
        same object.
        """
        self.assertQuerysetEqual(
                Number.objects.all(),
                [
                    '<Number: -1, -1.000>',
                    '<Number: 42, 42.000>',
                    '<Number: 1337, 1337.000>'
                ]
        )

    def test_increment_value(self):
        """
        We can increment a value of all objects in a query set.
        """
        self.assertEqual(
            Number.objects.filter(integer__gt=0)
                  .update(integer=F('integer') + 1),
            2)

        self.assertQuerysetEqual(
                Number.objects.all(),
                [
                    '<Number: -1, -1.000>',
                    '<Number: 43, 42.000>',
                    '<Number: 1338, 1337.000>'
                ]
        )

    def test_filter_not_equals_other_field(self):
        """
        We can filter for objects, where a value is not equals the value
        of an other field.
        """
        self.assertEqual(
            Number.objects.filter(integer__gt=0)
                  .update(integer=F('integer') + 1),
            2)
        self.assertQuerysetEqual(
                Number.objects.exclude(float=F('integer')),
                [
                    '<Number: 43, 42.000>',
                    '<Number: 1338, 1337.000>'
                ]
        )

    def test_complex_expressions(self):
        """
        Complex expressions of different connection types are possible.
        """
        n = Number.objects.create(integer=10, float=123.45)
        self.assertEqual(Number.objects.filter(pk=n.pk)
                                .update(float=F('integer') + F('float') * 2),
                          1)

        self.assertEqual(Number.objects.get(pk=n.pk).integer, 10)
        self.assertEqual(Number.objects.get(pk=n.pk).float, Approximate(256.900, places=3))

class ExpressionOperatorTests(TestCase):
    def setUp(self):
        self.n = Number.objects.create(integer=42, float=15.5)

    def test_lefthand_addition(self):
        # LH Addition of floats and integers
        Number.objects.filter(pk=self.n.pk).update(
            integer=F('integer') + 15,
            float=F('float') + 42.7
        )

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 57)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(58.200, places=3))

    def test_lefthand_subtraction(self):
        # LH Subtraction of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') - 15,
                                              float=F('float') - 42.7)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 27)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(-27.200, places=3))

    def test_lefthand_multiplication(self):
        # Multiplication of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') * 15,
                                              float=F('float') * 42.7)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 630)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(661.850, places=3))

    def test_lefthand_division(self):
        # LH Division of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') / 2,
                                              float=F('float') / 42.7)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 21)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(0.363, places=3))

    def test_lefthand_modulo(self):
        # LH Modulo arithmetic on integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') % 20)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 2)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    def test_lefthand_bitwise_and(self):
        # LH Bitwise ands on integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') & 56)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 40)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    @skipUnlessDBFeature('supports_bitwise_or')
    def test_lefthand_bitwise_or(self):
        # LH Bitwise or on integers
        Number.objects.filter(pk=self.n.pk).update(integer=F('integer') | 48)

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 58)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    def test_right_hand_addition(self):
        # Right hand operators
        Number.objects.filter(pk=self.n.pk).update(integer=15 + F('integer'),
                                              float=42.7 + F('float'))

        # RH Addition of floats and integers
        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 57)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(58.200, places=3))

    def test_right_hand_subtraction(self):
        Number.objects.filter(pk=self.n.pk).update(integer=15 - F('integer'),
                                              float=42.7 - F('float'))

        # RH Subtraction of floats and integers
        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, -27)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(27.200, places=3))

    def test_right_hand_multiplication(self):
        # RH Multiplication of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=15 * F('integer'),
                                              float=42.7 * F('float'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 630)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(661.850, places=3))

    def test_right_hand_division(self):
        # RH Division of floats and integers
        Number.objects.filter(pk=self.n.pk).update(integer=640 / F('integer'),
                                              float=42.7 / F('float'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 15)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(2.755, places=3))

    def test_right_hand_modulo(self):
        # RH Modulo arithmetic on integers
        Number.objects.filter(pk=self.n.pk).update(integer=69 % F('integer'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 27)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    def test_right_hand_bitwise_and(self):
        # RH Bitwise ands on integers
        Number.objects.filter(pk=self.n.pk).update(integer=15 & F('integer'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 10)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

    @skipUnlessDBFeature('supports_bitwise_or')
    def test_right_hand_bitwise_or(self):
        # RH Bitwise or on integers
        Number.objects.filter(pk=self.n.pk).update(integer=15 | F('integer'))

        self.assertEqual(Number.objects.get(pk=self.n.pk).integer, 47)
        self.assertEqual(Number.objects.get(pk=self.n.pk).float, Approximate(15.500, places=3))

