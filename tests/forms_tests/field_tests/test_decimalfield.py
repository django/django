import decimal

from django.forms import DecimalField, NumberInput, ValidationError, Widget
from django.test import SimpleTestCase
from django.utils import formats, translation

from . import FormFieldAssertionsMixin


class DecimalFieldTest(FormFieldAssertionsMixin, SimpleTestCase):

    def test_decimalfield_1(self):
        f = DecimalField(max_digits=4, decimal_places=2)
        self.assertWidgetRendersTo(f, '<input id="id_f" step="0.01" type="number" name="f" required />')
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('')
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertEqual(f.clean('1'), decimal.Decimal("1"))
        self.assertIsInstance(f.clean('1'), decimal.Decimal)
        self.assertEqual(f.clean('23'), decimal.Decimal("23"))
        self.assertEqual(f.clean('3.14'), decimal.Decimal("3.14"))
        self.assertEqual(f.clean(3.14), decimal.Decimal("3.14"))
        self.assertEqual(f.clean(decimal.Decimal('3.14')), decimal.Decimal("3.14"))
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('NaN')
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('Inf')
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('-Inf')
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('a')
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('łąść')
        self.assertEqual(f.clean('1.0 '), decimal.Decimal("1.0"))
        self.assertEqual(f.clean(' 1.0'), decimal.Decimal("1.0"))
        self.assertEqual(f.clean(' 1.0 '), decimal.Decimal("1.0"))
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('1.0a')
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 4 digits in total.'"):
            f.clean('123.45')
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 decimal places.'"):
            f.clean('1.234')
        msg = "'Ensure that there are no more than 2 digits before the decimal point.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('123.4')
        self.assertEqual(f.clean('-12.34'), decimal.Decimal("-12.34"))
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 4 digits in total.'"):
            f.clean('-123.45')
        self.assertEqual(f.clean('-.12'), decimal.Decimal("-0.12"))
        self.assertEqual(f.clean('-00.12'), decimal.Decimal("-0.12"))
        self.assertEqual(f.clean('-000.12'), decimal.Decimal("-0.12"))
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 decimal places.'"):
            f.clean('-000.123')
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 4 digits in total.'"):
            f.clean('-000.12345')
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean('--0.12')
        self.assertEqual(f.max_digits, 4)
        self.assertEqual(f.decimal_places, 2)
        self.assertIsNone(f.max_value)
        self.assertIsNone(f.min_value)

    def test_decimalfield_2(self):
        f = DecimalField(max_digits=4, decimal_places=2, required=False)
        self.assertIsNone(f.clean(''))
        self.assertIsNone(f.clean(None))
        self.assertEqual(f.clean('1'), decimal.Decimal("1"))
        self.assertEqual(f.max_digits, 4)
        self.assertEqual(f.decimal_places, 2)
        self.assertIsNone(f.max_value)
        self.assertIsNone(f.min_value)

    def test_decimalfield_3(self):
        f = DecimalField(
            max_digits=4, decimal_places=2,
            max_value=decimal.Decimal('1.5'),
            min_value=decimal.Decimal('0.5')
        )
        self.assertWidgetRendersTo(
            f,
            '<input step="0.01" name="f" min="0.5" max="1.5" type="number" id="id_f" required />',
        )
        with self.assertRaisesMessage(ValidationError, "'Ensure this value is less than or equal to 1.5.'"):
            f.clean('1.6')
        with self.assertRaisesMessage(ValidationError, "'Ensure this value is greater than or equal to 0.5.'"):
            f.clean('0.4')
        self.assertEqual(f.clean('1.5'), decimal.Decimal("1.5"))
        self.assertEqual(f.clean('0.5'), decimal.Decimal("0.5"))
        self.assertEqual(f.clean('.5'), decimal.Decimal("0.5"))
        self.assertEqual(f.clean('00.50'), decimal.Decimal("0.50"))
        self.assertEqual(f.max_digits, 4)
        self.assertEqual(f.decimal_places, 2)
        self.assertEqual(f.max_value, decimal.Decimal('1.5'))
        self.assertEqual(f.min_value, decimal.Decimal('0.5'))

    def test_decimalfield_4(self):
        f = DecimalField(decimal_places=2)
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 decimal places.'"):
            f.clean('0.00000001')

    def test_decimalfield_5(self):
        f = DecimalField(max_digits=3)
        # Leading whole zeros "collapse" to one digit.
        self.assertEqual(f.clean('0000000.10'), decimal.Decimal("0.1"))
        # But a leading 0 before the . doesn't count towards max_digits
        self.assertEqual(f.clean('0000000.100'), decimal.Decimal("0.100"))
        # Only leading whole zeros "collapse" to one digit.
        self.assertEqual(f.clean('000000.02'), decimal.Decimal('0.02'))
        with self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 3 digits in total.'"):
            f.clean('000000.0002')
        self.assertEqual(f.clean('.002'), decimal.Decimal("0.002"))

    def test_decimalfield_6(self):
        f = DecimalField(max_digits=2, decimal_places=2)
        self.assertEqual(f.clean('.01'), decimal.Decimal(".01"))
        msg = "'Ensure that there are no more than 0 digits before the decimal point.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('1.1')

    def test_decimalfield_scientific(self):
        f = DecimalField(max_digits=2, decimal_places=2)
        self.assertEqual(f.clean('1E+2'), decimal.Decimal('1E+2'))
        self.assertEqual(f.clean('1e+2'), decimal.Decimal('1E+2'))
        with self.assertRaisesMessage(ValidationError, "Ensure that there are no more"):
            f.clean('0.546e+2')

    def test_decimalfield_widget_attrs(self):
        f = DecimalField(max_digits=6, decimal_places=2)
        self.assertEqual(f.widget_attrs(Widget()), {})
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': '0.01'})
        f = DecimalField(max_digits=10, decimal_places=0)
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': '1'})
        f = DecimalField(max_digits=19, decimal_places=19)
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': '1e-19'})
        f = DecimalField(max_digits=20)
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': 'any'})
        f = DecimalField(max_digits=6, widget=NumberInput(attrs={'step': '0.01'}))
        self.assertWidgetRendersTo(f, '<input step="0.01" name="f" type="number" id="id_f" required />')

    def test_decimalfield_localized(self):
        """
        A localized DecimalField's widget renders to a text input without
        number input specific attributes.
        """
        f = DecimalField(localize=True)
        self.assertWidgetRendersTo(f, '<input id="id_f" name="f" type="text" required />')

    def test_decimalfield_changed(self):
        f = DecimalField(max_digits=2, decimal_places=2)
        d = decimal.Decimal("0.1")
        self.assertFalse(f.has_changed(d, '0.10'))
        self.assertTrue(f.has_changed(d, '0.101'))

        with translation.override('fr'), self.settings(USE_L10N=True):
            f = DecimalField(max_digits=2, decimal_places=2, localize=True)
            localized_d = formats.localize_input(d)  # -> '0,1' in French
            self.assertFalse(f.has_changed(d, localized_d))
