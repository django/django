from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils import six


def format(number, decimal_sep, decimal_pos=None, grouping=0, thousand_sep='', force_grouping=False):
    """
    Gets a number (as a number or string), and returns it as a string,
    using formats defined as arguments:

    * decimal_sep: Decimal separator symbol (for example ".")
    * decimal_pos: Number of decimal positions
    * grouping: Number of digits in every group limited by thousand separator
    * thousand_sep: Thousand separator symbol (for example ",")
    """
    use_grouping = settings.USE_L10N and settings.USE_THOUSAND_SEPARATOR
    use_grouping = use_grouping or force_grouping
    use_grouping = use_grouping and grouping > 0
    use_grouping = use_grouping and thousand_sep

    # Make the common case fast
    if isinstance(number, int) and not use_grouping and not decimal_pos:
        return mark_safe(six.text_type(number))

    float_number = float(number)
    str_number = six.text_type(number)

    if decimal_pos is not None:
        # Use the %f format string. This gives us rounding and the
        # right number of decimal positions automatically. This also
        # removes any 'e' if the number is really small or really large
        str_number = six.text_type(('%.' + str(decimal_pos) + 'f') % float_number)

    if not use_grouping:
        return str_number.replace('.', decimal_sep)

    # For grouping, we need to separate the sign, int_part and decimal part
    if float_number < 0:
        sign = '-'
        str_number = str_number[1:]
    else:
        sign = ''

    if decimal_pos is not None or '.' in str_number:
        int_part, dec_part = str_number.split('.')
        dec_part = decimal_sep + dec_part
    else:
        int_part, dec_part = str_number, ''

    first_part_len = len(int_part) % grouping
    full_parts = int_part[first_part_len:]
    groups = [full_parts[i:i+grouping] for i in range(0, len(full_parts), grouping)]

    if first_part_len > 0:
        groups.insert(0, int_part[0:first_part_len])

    return sign + thousand_sep.join(groups) + dec_part
