import datetime

def id_number_checksum(gd):
    """
    Calculates a Swedish ID number checksum, using the
    "Luhn"-algoritm
    """
    n = s = 0
    for c in (gd['year'] + gd['month'] + gd['day'] + gd['serial']):
        tmp = ((n % 2) and 1 or 2) * int(c)

        if tmp > 9:
            tmp = sum([int(i) for i in str(tmp)])

        s += tmp
        n += 1

    if (s % 10) == 0:
        return 0

    return (((s // 10) + 1) * 10) - s

def validate_id_birthday(gd, fix_coordination_number_day=True):
    """
    Validates the birth_day and returns the datetime.date object for
    the birth_day.

    If the date is an invalid birth day, a ValueError will be raised.
    """

    today = datetime.date.today()

    day = int(gd['day'])
    if fix_coordination_number_day and day > 60:
        day -= 60

    if gd['century'] is None:

        # The century was not specified, and need to be calculated from todays date
        current_year = today.year
        year = int(today.strftime('%Y')) - int(today.strftime('%y')) + int(gd['year'])

        if ('%s%s%02d' % (gd['year'], gd['month'], day)) > today.strftime('%y%m%d'):
            year -= 100

        # If the person is older than 100 years
        if gd['sign'] == '+':
            year -= 100
    else:
        year = int(gd['century'] + gd['year'])

        # Make sure the year is valid
        # There are no swedish personal identity numbers where year < 1800
        if year < 1800:
            raise ValueError

    # ValueError will be raise for invalid dates
    birth_day = datetime.date(year, int(gd['month']), day)

    # birth_day must not be in the future
    if birth_day > today:
        raise ValueError

    return birth_day

def format_personal_id_number(birth_day, gd):
    # birth_day.strftime cannot be used, since it does not support dates < 1900
    return unicode(str(birth_day.year) + gd['month'] + gd['day'] + gd['serial'] + gd['checksum'])

def format_organisation_number(gd):
    if gd['century'] is None:
        century = ''
    else:
        century = gd['century']

    return unicode(century + gd['year'] + gd['month'] + gd['day'] + gd['serial'] + gd['checksum'])

def valid_organisation(gd):
    return gd['century'] in (None, 16) and \
        int(gd['month']) >= 20 and \
        gd['sign'] in (None, '-') and \
        gd['year'][0] in ('2', '5', '7', '8', '9') # group identifier

