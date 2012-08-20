from django.utils.encoding import smart_text

def ssn_check_digit(value):
    "Calculate Italian social security number check digit."
    ssn_even_chars = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
        '9': 9, 'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7,
        'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15,
        'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23,
        'Y': 24, 'Z': 25
    }
    ssn_odd_chars = {
        '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8':
        19, '9': 21, 'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15,
        'H': 17, 'I': 19, 'J': 21, 'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11,
        'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14, 'U': 16, 'V': 10, 'W': 22,
        'X': 25, 'Y': 24, 'Z': 23
    }
    # Chars from 'A' to 'Z'
    ssn_check_digits = [chr(x) for x in range(65, 91)]

    ssn = value.upper()
    total = 0
    for i in range(0, 15):
        try:
            if i % 2 == 0:
                total += ssn_odd_chars[ssn[i]]
            else:
                total += ssn_even_chars[ssn[i]]
        except KeyError:
            msg = "Character '%(char)s' is not allowed." % {'char': ssn[i]}
            raise ValueError(msg)
    return ssn_check_digits[total % 26]

def vat_number_check_digit(vat_number):
    "Calculate Italian VAT number check digit."
    normalized_vat_number = smart_text(vat_number).zfill(10)
    total = 0
    for i in range(0, 10, 2):
        total += int(normalized_vat_number[i])
    for i in range(1, 11, 2):
        quotient , remainder = divmod(int(normalized_vat_number[i]) * 2, 10)
        total += quotient + remainder
    return smart_text((10 - total % 10) % 10)
