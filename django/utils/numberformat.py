from decimal import Decimal

from django.conf import settings
from django.utils.safestring import SafeString


def format(number, decimal_sep, decimal_pos=None, grouping=0, thousand_sep='',
           force_grouping=False, use_l10n=None):
    """
    Get a number (as a number or string), and return it as a string,
    using formats defined as arguments:

    * decimal_sep: Decimal separator symbol (for example ".")
    * decimal_pos: Number of decimal positions
    * grouping: Number of digits in every group limited by thousand separator.
        For non-uniform digit grouping, it can be a sequence with the number
        of digit group sizes following the format used by the Python locale
        module in locale.localeconv() LC_NUMERIC grouping (e.g. (3, 2, 0)).
    * thousand_sep: Thousand separator symbol (for example ",")
    """
    if force_grouping:
        pass
    elif not settings.USE_THOUSAND_SEPARATOR:
        grouping = 0
    elif use_l10n is False:
        grouping = 0
    elif use_l10n is None and not settings.USE_L10N:
        grouping = 0

    # Make the common case fast
    if isinstance(number, int) and (grouping == 0 or grouping == 3):
        return _format_int(number, decimal_sep, decimal_pos, thousand_sep, grouping)

    # Handle Decimals
    if isinstance(number, Decimal):
        return _format_dec(number, decimal_sep, decimal_pos, thousand_sep, grouping)

    # Don't unnecessarily convert number to string for speed
    if isinstance(number, str):
        return _format_string(number, decimal_sep, decimal_pos, thousand_sep, grouping)

    str_number = str(number)
    # Treat potentially very large/small floats as Decimals.
    if isinstance(number, float) and 'e' in str_number.lower():
        return _format_dec(Decimal(str_number), decimal_sep, decimal_pos, thousand_sep, grouping)

    # Format all other cases as a string
    return _format_string(str_number, decimal_sep, decimal_pos, thousand_sep, grouping)


def _format_int(number, decimal_sep, decimal_pos, thousand_sep, grouping):
    """
    Formats an integer, returning it as a string.

    This function should only be used when grouping is 0 or 3. See
    numberformat.format docstring for details about arguments.
    """
    if grouping and (number > 999 or number < -999):
        # f'{number:,}' returns a string with a ',' as a thousand separator
        number = f'{number:,}'.replace(',', thousand_sep)
    else:
        # It is unclear as to why this case should be marked safe, but
        # we return SafeString here to avoid a change in functionality
        # from the previous implementation of format.
        number = SafeString(number)
    if decimal_pos:
        return number + decimal_sep + '0' * decimal_pos
    return number


def _format_dec(number, decimal_sep, decimal_pos, thousand_sep, grouping):
    """
    Gets a number as a Decimal instance, and formats it as a string.

    See numberformat.format docstring for details about arguments.
    """
    if decimal_pos is not None:
        # If the provided number is too small to affect any of the visible
        # decimal places, consider it equal to '0'.
        cutoff = Decimal('0.' + '1'.rjust(decimal_pos, '0'))
        if abs(number) < cutoff:
            if decimal_pos:
                return '0' + decimal_sep + '0' * decimal_pos
            return '0'
    # Format values with more than 200 digits (an arbitrary cutoff) using
    # scientific notation to avoid high memory usage in {:f}'.format().
    _, digits, exponent = number.as_tuple()
    if abs(exponent) + len(digits) > 200:
        number = f'{number:e}'
        coefficient, exponent = number.split('e')
        # Format the coefficient.
        coefficient = _format_string(
            coefficient, decimal_sep, decimal_pos,
            thousand_sep, grouping,
        )
        return f'{coefficient}e{exponent}'

    number = f'{number:f}'
    return _format_string(number, decimal_sep, decimal_pos, thousand_sep, grouping)


def _format_string(str_number, decimal_sep, decimal_pos, thousand_sep, grouping):
    """
    Gets a number as a string, and formats it as a string.

    See numberformat.format docstring for details about arguments.
    """
    sign = ''
    if str_number[0] == '-':
        sign = '-'
        str_number = str_number[1:]

    # Get int_part, and dec_part
    if '.' in str_number:
        int_part, dec_part = str_number.split('.')
        if decimal_pos is not None:
            dec_part = dec_part[:decimal_pos]
    else:
        int_part, dec_part = str_number, ''
    if decimal_pos is not None:
        dec_part = dec_part + ('0' * (decimal_pos - len(dec_part)))
    dec_part = dec_part and decimal_sep + dec_part

    # grouping
    if grouping == 3:
        # Use builtins.format where we can for speed.
        int_part = f'{int(int_part):,}'
        if thousand_sep != ',':
            int_part = int_part.replace(',', thousand_sep)
    elif grouping:
        try:
            # if grouping is a sequence
            intervals = list(grouping)
        except TypeError:
            # grouping is a single value
            intervals = [grouping, 0]
        active_interval = intervals.pop(0)
        int_part_gd = ''
        cnt = 0
        for digit in int_part[::-1]:
            if cnt and cnt == active_interval:
                if intervals:
                    active_interval = intervals.pop(0) or active_interval
                int_part_gd += thousand_sep[::-1]
                cnt = 0
            int_part_gd += digit
            cnt += 1
        int_part = int_part_gd[::-1]
    return sign + int_part + dec_part
