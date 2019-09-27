from decimal import Decimal
from sys import float_info
from unittest import mock

from django.test import SimpleTestCase
from django.utils.numberformat import (
    _format_dec, _format_int, _format_string, format as nformat,
)


class EuroDecimal(Decimal):
    """
    Wrapper for Decimal which prefixes each amount with the € symbol.
    """
    def __format__(self, specifier, **kwargs):
        amount = super().__format__(specifier, **kwargs)
        return '€ {}'.format(amount)


@mock.patch("django.utils.numberformat._format_string")
@mock.patch("django.utils.numberformat._format_dec")
@mock.patch("django.utils.numberformat._format_int")
class TestNumberFormat(SimpleTestCase):
    def test_grouping_behaviour(self, mock_f_int, mock_f_dec, mock_f_string):
        tests = [
            (   # use_l10n should over-write settings.USE_L10N(True)
                {"use_l10n": False},
                {"USE_THOUSAND_SEPARATOR": True, "USE_L10N": True},
                0
            ),
            (   # When use_l10n is None, settings.USE_L10N(True) should be used
                {},
                {"USE_THOUSAND_SEPARATOR": True, "USE_L10N": True},
                3
            ),
            (   # force_grouping takes precedence over use_l10n
                {"use_l10n": False, "force_grouping": True},
                {"USE_THOUSAND_SEPARATOR": True, "USE_L10N": True},
                3
            ),
            (   # use_l10n should over-write settings.USE_L10N(False)
                {"use_l10n": True},
                {"USE_THOUSAND_SEPARATOR": True, "USE_L10N": False},
                3
            ),
            (   # When use_l10n == None, settings.USE_L10N(False) should be used
                {},
                {"USE_THOUSAND_SEPARATOR": True, "USE_L10N": False},
                0
            ),
            (   # settings.USE_THOUSAND_SEPARATOR takes precedence over use_l10n
                {"use_l10n": True},
                {"USE_THOUSAND_SEPARATOR": False, "USE_L10N": True},
                0
            ),
            (   # settings.USE_THOUSAND_SEPARATOR takes precedence over settings.USE_L10N
                {},
                {"USE_THOUSAND_SEPARATOR": False, "USE_L10N": True},
                0
            ),
            (   # force_grouping takes precedence over settings.USE_THOUSAND_SEPARATOR
                {"force_grouping": True},
                {"USE_THOUSAND_SEPARATOR": False, "USE_L10N": True},
                3
            ),
        ]

        for [args, settings, expected] in tests:
            with self.settings(**settings):
                with self.subTest(settings=settings):
                    nformat(1234, ".", grouping=3, **args)
                    mock_f_int.assert_called_once_with(1234, ".", None, "", expected)
                    mock_f_int.reset_mock()

                    nformat('1234', ".", grouping=3, **args)
                    mock_f_string.assert_called_once_with('1234', ".", None, "", expected)
                    mock_f_string.reset_mock()

                    nformat(Decimal(1234), ".", grouping=3, **args)
                    mock_f_dec.assert_called_once_with(Decimal(1234), ".", None, "", expected)
                    mock_f_dec.reset_mock()

    def test_types_are_handled_correctly(self, mock_f_int, mock_f_dec, mock_f_string):
        """
        Test that the correct sub-function is called for different types.
        """
        tests = [
            (123, mock_f_int, 123),
            ("123", mock_f_string, "123"),
            (Decimal(123), mock_f_dec, Decimal(123)),
            (123.45, mock_f_string, "123.45"),
            (EuroDecimal(123.45), mock_f_dec, EuroDecimal(123.45)),
            (9e-19, mock_f_dec, Decimal('9e-19')),                # Very Small Floats
            (0.000001, mock_f_dec, Decimal("1e-6")),
            (1E16, mock_f_dec, Decimal("1E16")),                  # Very Large Floats
            (100000000000000000000.0, mock_f_dec, Decimal('1e+20')),
            # A float without a fractional part (3.) results in a ".0" when no
            # decimal_pos is given. Contrast that with the Decimal('3.') case
            # in test_decimal_numbers which doesn't return a fractional part.
            (3., mock_f_string, "3.0"),


        ]
        for [number, expected_func, expected_arg] in tests:
            with self.subTest(number=number):
                nformat(number, ".")
                expected_func.assert_called_once_with(expected_arg, ".", None, "", 0)
                expected_func.reset_mock()

        # When grouping is not 0 or 3, integers should be converted to strings
        nformat(123, ".", grouping=3, force_grouping=True)
        mock_f_int.assert_called_once_with(123, ".", None, "", 3)
        mock_f_int.reset_mock()
        nformat(123, ".", grouping=2, force_grouping=True)
        mock_f_string.assert_called_once_with('123', ".", None, "", 2)
        mock_f_string.reset_mock()
        nformat(123, ".", grouping=(1, 2), force_grouping=True)
        mock_f_string.assert_called_once_with('123', ".", None, "", (1, 2))
        mock_f_string.reset_mock()


class TestNumberFormatInt(SimpleTestCase):
    def test_integers(self):
        tests = [
            (123, ".", None, "", 0, '123'),                    # Default
            (123456789, ".", None, ", ", 3, '123, 456, 789'),  # With Grouping (3s)
            (123456789, ".", None, "*", 3, '123*456*789'),     # With '*' as thousand_sep
            (123456789, ".", None, "", 3, '123456789'),        # With empty string thousand_sep
            (123456, ".", 0, "", 0, '123456'),                 # With 0 decimal places
            (123456, ".", 2, "", 0, '123456.00'),              # With 2 decimal places
            (123456, ", ", 2, "", 0, '123456, 00'),            # With ', ' as decimal_sep
            (123456, ".", 2, ", ", 3, '123, 456.00'),          # With 2 decimal places and grouping
            (-123, ".", None, "", 0, '-123'),                  # Negative number
            (-123456, ".", None, ", ", 3, '-123, 456'),        # Negative number with grouping
            (0, ".", 5, ", ", 3, '0.00000')                    # 0 with decimals and grouping
        ]
        for [number, *other_args, expected_value] in tests:
            with self.subTest(value=number):
                self.assertEqual(
                    _format_int(number, *other_args),
                    expected_value
                )

    def test_large_integers(self):
        most_max = (
            '{}179769313486231570814527423731704356798070567525844996'
            '598917476803157260780028538760589558632766878171540458953'
            '514382464234321326889464182768467546703537516986049910576'
            '551282076245490090389328944075868508455133942304583236903'
            '222948165808559332123348274797826204144723168738177180919'
            '29988125040402618412485836{}'
        )
        most_max2 = (
            '{}359, 538, 626, 972, 463, 141, 629, 054, 847, 463, 408, 713, 596, 141, '
            '135, 051, 689, 993, 197, 834, 953, 606, 314, 521, 560, 057, 077, 521, 179, '
            '117, 265, 533, 756, 343, 080, 917, 907, 028, 764, 928, 468, 642, 653, 778, '
            '928, 365, 536, 935, 093, 407, 075, 033, 972, 099, 821, 153, 102, 564, 152, '
            '490, 980, 180, 778, 657, 888, 151, 737, 016, 910, 267, 884, 609, 166, 473, '
            '806, 445, 896, 331, 617, 118, 664, 246, 696, 549, 595, 652, 408, 289, 446, '
            '337, 476, 354, 361, 838, 599, 762, 500, 808, 052, 368, 249, 716, 736{}'
        )

        int_max = int(float_info.max)

        tests = [
            (int_max, '.', None, ', ', 0, most_max.format('', '8')),        # Default
            (int_max + 1, '.', 2, ', ', 0, most_max.format('', '9.00')),    # 2 decimal places
            (int_max * 2, '.', None, ', ', 3, most_max2.format('', '')),    # Grouping (3s)
            (-1 * int_max, '.', None, ', ', 0, most_max.format('-', '8')),  # Negative number
            (-1 - int_max, '.', 2, ', ', 0, most_max.format('-', '9.00')),  # Negative number with 2 decimal places
            (-2 * int_max, '.', 2, ', ', 3, most_max2.format('-', '.00'))   # Negative, grouping with decimals
        ]
        for [number, *other_args, expected_value] in tests:
            with self.subTest(value=number):
                self.assertEqual(
                    _format_int(number, *other_args),
                    expected_value
                )


class TestNumberFormatDec(SimpleTestCase):
    def test_decimals(self):
        tests = [
            ('1234', '.', None, "", 0, '1234'),                           # Integer
            ('1234.2', '.', None, " ", 0, '1234.2'),                      # With decimal
            ('1234', '.', 2, ", ", 0, '1234.00'),                         # dec_pos specified
            ('12345', ".", 2, ", ", 2, "1, 23, 45.00"),                   # dec_pos specified, and grouping
            ('-1234.56', ', ', 1, 0, "", "-1234, 5"),                     # Negative
            ('9e-19', ".", 2, "", 3, "0.00"),                             # Small number with dec_pos
            ('0.0000099', ".", 0, "", 3, "0"),                            # Small number with dec_pos == 0
            ('1e16', ".", None, ", ", 3, '10, 000, 000, 000, 000, 000'),  # Grouping with large number
            ('1e13', ".", 2, ", ", 3, '10, 000, 000, 000, 000.00'),       # Grouping and decimals with large number
            ('3.', '.', None, "", 0, "3"),                                # With trailing decimal
            ('3.0', '.', None, "", 0, "3.0"),                             # With trailing 0
        ]
        for [number, *other_args, expected_value] in tests:
            with self.subTest(value=number):
                self.assertEqual(
                    _format_dec(Decimal(number), *other_args),
                    expected_value
                )

    def test_very_large_and_small_decimals(self):
        tests = [
            ('9e9999', None, '9e+9999'),
            ('9e9999', 3, '9.000e+9999'),
            ('9e201', None, '9e+201'),
            ('9e200', None, '9e+200'),
            ('1.2345e999', 2, '1.23e+999'),
            ('9e-999', None, '9e-999'),
            ('1e-7', 8, '0.00000010'),
            ('1e-8', 8, '0.00000001'),
            ('1e-9', 8, '0.00000000'),
            ('1e-10', 8, '0.00000000'),
            ('1e-11', 8, '0.00000000'),
            ('1' + ('0' * 300), 3, '1.000e+300'),
            ('0.{}1234'.format('0' * 299), 3, '0.000'),
        ]
        for value, decimal_pos, expected_value in tests:
            with self.subTest(value=value):
                self.assertEqual(
                    _format_dec(Decimal(value), '.', decimal_pos, "", 0),
                    expected_value
                )

    def test_decimal_subclass(self):
        price = EuroDecimal('1.23')
        self.assertEqual(_format_dec(price, ', ', None, "", 0), '€ 1, 23')


class TestNumberFormatString(SimpleTestCase):
    def test_strings(self):
        tests = [
            ('123.23', ".", None, "", 0, '123.23'),               # Default
            ('123456789', ".", None, ", ", 3, '123, 456, 789'),   # With Grouping (3s)
            ('123456789.0', ".", None, "*", 3, '123*456*789.0'),  # With '*' as thousand_sep
            ('123456789', ".", None, "", 3, '123456789'),         # With empty string thousand_sep
            ('123456.99', ".", 0, "", 0, '123456'),               # With 0 decimal places
            ('123456.009', ".", 2, "", 0, '123456.00'),           # With 2 decimal places
            ('123456', ", ", 2, "", 0, '123456, 00'),             # With ', ' as decimal_sep
            ('123456.2', ".", 4, ", ", 3, '123, 456.2000'),       # With 4 decimal places and grouping
            ('-123.0', ".", None, "", 0, '-123.0'),               # Negative number
            ('-123456', ".", None, ", ", 2, '-12, 34, 56'),       # Negative number with grouping (2s)
            ('0', ".", 5, ", ", 3, '0.00000')                     # 0 with decimals and grouping
        ]
        for [number, *other_args, expected_value] in tests:
            with self.subTest(value=number):
                self.assertEqual(
                    _format_string(number, *other_args),
                    expected_value
                )

    def test_string_tuple_groupings(self):
        tests = [
            ("123456789", ".", None, ", ", (3, ), '123, 456, 789'),
            ("123456789", ".", None, ", ", (3, 2), '12, 34, 56, 789'),
            ("56789123456789", ".", None, ", ", (3, 5, 1), '5, 6, 7, 8, 9, 1, 23456, 789')
        ]
        for [number, *other_args, expected_value] in tests:
            with self.subTest(value=number):
                self.assertEqual(
                    _format_string(number, *other_args),
                    expected_value
                )
