from decimal import Decimal, localcontext

from django.template.defaultfilters import floatformat
from django.test import SimpleTestCase
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
        self.assertEqual(floatformat(-0.7), '-0.7')
        self.assertEqual(floatformat(0.07), '0.1')
        self.assertEqual(floatformat(-0.07), '-0.1')
        self.assertEqual(floatformat(0.007), '0.0')
        self.assertEqual(floatformat(0.0), '0')
        self.assertEqual(floatformat(7.7, 0), '8')
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
        self.assertEqual(floatformat(-1.323297138040798e+35, 2), '-132329713804079800000000000000000000.00')
        self.assertEqual(floatformat(-1.323297138040798e+35, -2), '-132329713804079800000000000000000000')
        self.assertEqual(floatformat(1.5e-15, 20), '0.00000000000000150000')
        self.assertEqual(floatformat(1.5e-15, -20), '0.00000000000000150000')
        self.assertEqual(floatformat(1.00000000000000015, 16), '1.0000000000000002')

    def test_zero_values(self):
        self.assertEqual(floatformat(0, 6), '0.000000')
        self.assertEqual(floatformat(0, 7), '0.0000000')
        self.assertEqual(floatformat(0, 10), '0.0000000000')
        self.assertEqual(floatformat(0.000000000000000000015, 20), '0.00000000000000000002')

    def test_negative_zero_values(self):
        tests = [
            (-0.01, -1, '0.0'),
            (-0.001, 2, '0.00'),
            (-0.499, 0, '0'),
        ]
        for num, decimal_places, expected in tests:
            with self.subTest(num=num, decimal_places=decimal_places):
                self.assertEqual(floatformat(num, decimal_places), expected)

    def test_infinity(self):
        pos_inf = float(1e30000)
        neg_inf = float(-1e30000)
        self.assertEqual(floatformat(pos_inf), 'inf')
        self.assertEqual(floatformat(neg_inf), '-inf')
        self.assertEqual(floatformat(pos_inf / pos_inf), 'nan')

    def test_float_dunder_method(self):
        class FloatWrapper:
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
