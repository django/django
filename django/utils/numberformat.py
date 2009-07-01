def format(number, decimal_sep, decimal_pos, groupping=0, thousand_sep=''):
    """
    """
    # sign
    if number < 0:
        sign = '-'
    else:
        sign = ''
    # decimal part
    str_number = str(abs(number))
    if '.' in str_number:
        int_part, dec_part = str_number.split('.')
        dec_part = dec_part[:decimal_pos]
    else:
        int_part, dec_part = str_number, ''
    dec_part = dec_part + ('0' * (decimal_pos - len(dec_part)))
    if dec_part: dec_part = decimal_sep + dec_part
    # groupping
    if groupping:
        int_part_gd = ''
        for cnt, digit in enumerate(int_part[::-1]):
            if cnt and not cnt % groupping:
                int_part_gd += thousand_sep
            int_part_gd += digit
        int_part = int_part_gd[::-1]


    return sign + int_part + dec_part

if __name__ == '__main__':
    import decimal
    print format_number(-1000000, ',', 4, 3, '.')
    print format_number(-100.100, ',', 4, 3, '.')
    print format_number(decimal.Decimal('1000.100'), ',', 4)
