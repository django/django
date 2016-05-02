# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal, localcontext
from unittest import expectedFailure

from django.template.defaultfilters import floatformat
from django.test import SimpleTestCase
from django.utils import six
from django.utils.safestring import mark_safe

from ..utils import setup


class FloatformatTests(SimpleTestCase):

    @setup({'floatformat01': '{% autoescape off %}{{ a|floatformat }} {{ b|floatformat }}{% endautoescape %}'})
    def test_floatformat01(self):
        output = self.engine.render_to_string('floatformat01', {"a": "1.42", "b": mark_safe("1.42")})
        self.assertEqual(output, "1.4 1.4")

    @setup({'floatformat02': '{{ a|floatformat }} {{ b|floatformat }}'})
    def test_floatformat02(self):
        output = self.engine.render_to_string('floatformat02', {"a": "1.42", "b": mark_safe("1.42")})
        self.assertEqual(output, "1.4 1.4")


class FunctionTests(SimpleTestCase):

    def test_inputs(self):
        self.assertEqual(floatformat(7.7), '7.7')
        self.assertEqual(floatformat(7.0), '7')
        self.assertEqual(floatformat(0.7), '0.7')
        self.assertEqual(floatformat(0.07), '0.1')
        self.assertEqual(floatformat(0.007), '0.0')
        self.assertEqual(floatformat(0.0), '0')
        self.assertEqual(floatformat(7.7, 3), '7.700')
        self.assertEqual(floatformat(6.000000, 3), '6.000')
        self.assertEqual(floatformat(6.200000, 3), '6.200')
        self.assertEqual(floatformat(6.200000, -3), '6.200')
        self.assertEqual(floatformat(13.1031, -3), '13.103')
        self.assertEqual(floatformat(11.1197, -2), '11.12')
        self.assertEqual(floatformat(11.0000, -2), '11')
        self.assertEqual(floatformat(11.000001, -2), '11.00')
        self.assertEqual(floatformat(8.2798, 3), '8.280')
        self.assertEqual(floatformat(5555.555, 2), '5555.56')
        self.assertEqual(floatformat(001.3000, 2), '1.30')
        self.assertEqual(floatformat(0.12345, 2), '0.12')
        self.assertEqual(floatformat(Decimal('555.555'), 2), '555.56')
        self.assertEqual(floatformat(Decimal('09.000')), '9')
        self.assertEqual(floatformat('foo'), '')
        self.assertEqual(floatformat(13.1031, 'bar'), '13.1031')
        self.assertEqual(floatformat(18.125, 2), '18.13')
        self.assertEqual(floatformat('foo', 'bar'), '')
        self.assertEqual(floatformat('¿Cómo esta usted?'), '')
        self.assertEqual(floatformat(None), '')

    def test_zero_values(self):
        """
        Check that we're not converting to scientific notation.
        """
        self.assertEqual(floatformat(0, 6), '0.000000')
        self.assertEqual(floatformat(0, 7), '0.0000000')
        self.assertEqual(floatformat(0, 10), '0.0000000000')
        self.assertEqual(floatformat(0.000000000000000000015, 20),
                         '0.00000000000000000002')

    def test_infinity(self):
        pos_inf = float(1e30000)
        self.assertEqual(floatformat(pos_inf), six.text_type(pos_inf))

        neg_inf = float(-1e30000)
        self.assertEqual(floatformat(neg_inf), six.text_type(neg_inf))

        nan = pos_inf / pos_inf
        self.assertEqual(floatformat(nan), six.text_type(nan))

    def test_float_dunder_method(self):
        class FloatWrapper(object):
            def __init__(self, value):
                self.value = value

            def __float__(self):
                return self.value

        self.assertEqual(floatformat(FloatWrapper(11.000001), -2), '11.00')

    def test_low_decimal_precision(self):
        """
        #15789
        """
        with localcontext() as ctx:
            ctx.prec = 2
            self.assertEqual(floatformat(1.2345, 2), '1.23')
            self.assertEqual(floatformat(15.2042, -3), '15.204')
            self.assertEqual(floatformat(1.2345, '2'), '1.23')
            self.assertEqual(floatformat(15.2042, '-3'), '15.204')
            self.assertEqual(floatformat(Decimal('1.2345'), 2), '1.23')
            self.assertEqual(floatformat(Decimal('15.2042'), -3), '15.204')

    def test_many_zeroes(self):
        self.assertEqual(floatformat(1.00000000000000015, 16), '1.0000000000000002')

    if six.PY2:
        # The above test fails because of Python 2's float handling. Floats
        # with many zeroes after the decimal point should be passed in as
        # another type such as unicode or Decimal.
        test_many_zeroes = expectedFailure(test_many_zeroes)
