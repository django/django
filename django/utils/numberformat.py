from __future__ import unicode_literals

from decimal import Decimal

from django.conf import settings
from django.utils import six
from django.utils.six.moves.builtins import format as _format


def format(number, decimal_sep, decimal_pos=None, grouping=0, thousand_sep='',
           force_grouping=False):
    """
    Gets a number (as a number or string), and returns it as a string,
    using formats defined as arguments:

    * decimal_sep: Decimal separator symbol (for example ".")
    * decimal_pos: Number of decimal positions
    * grouping: Number of digits in every group limited by thousand separator
    * thousand_sep: Thousand separator symbol (for example ",")
    """
    use_grouping = grouping > 0 and (force_grouping or
                                     (settings.USE_THOUSAND_SEPARATOR and settings.USE_L10N))
    if not use_grouping or grouping == 3:
        try:
            # Make the common case fast
            #
            # Works on numbers when the formatting can be handled by the built in format
            # function (e.g. grouping is disabled or 3).
            #
            # Will also work on strings when grouping is disabled and decimal_pos is None.
            if decimal_pos is not None:
                # Add one toe decimal_pos to prevent visible rounding. For example:
                # If `number` is 10.888 and `decimal_pos` is 2 return 10.88 not 10.89.
                format_string = '.%sf' % (decimal_pos + 1)
            elif isinstance(number, Decimal):
                format_string = 'f'
            else:
                format_string = ''
            if use_grouping and (number >= 1000 or number <= -1000):
                format_string = ',' + format_string  # PEP 0378
            if format_string == '':
                return six.text_type(number).replace('.', decimal_sep)
            int_part, sep, dec_part = _format(number, format_string).partition('.')
            if decimal_pos is not None:
                dec_part = dec_part.ljust(decimal_pos, '0')[:decimal_pos]
            if dec_part:
                return int_part.replace(',', thousand_sep) + decimal_sep + dec_part
            return int_part.replace(',', thousand_sep)
        except (TypeError, ValueError):
            pass
    # The slow path, works on strings (and numbers when grouping is enabled and not 3).
    if isinstance(number, Decimal):
        str_number = _format(number, 'f')
    else:
        str_number = six.text_type(number)
    # sign
    sign = ''
    if str_number[0] == '-':
        sign = '-'
        str_number = str_number[1:]
    # decimal part
    int_part, sep, dec_part = str_number.partition('.')
    if decimal_pos is not None:
        dec_part = dec_part.ljust(decimal_pos, '0')[:decimal_pos]
    # grouping
    if use_grouping and len(int_part) > grouping:
        int_part_gd = ''
        for cnt, digit in enumerate(reversed(int_part)):
            if cnt and not cnt % grouping:
                int_part_gd += thousand_sep[::-1]
            int_part_gd += digit
        int_part = int_part_gd[::-1]
    if dec_part:
        return sign + int_part + decimal_sep + dec_part
    return sign + int_part
