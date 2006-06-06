from django import template
import re

register = template.Library()

def ordinal(value):
    """
    Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except ValueError:
        return value
    t = ('th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th')
    if value % 100 in (11, 12, 13): # special case
        return '%dth' % value
    return '%d%s' % (value, t[value % 10])
register.filter(ordinal)

def intcomma(value):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    orig = str(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', str(value))
    if orig == new:
        return new
    else:
        return intcomma(new)
register.filter(intcomma)

def intword(value):
    """
    Converts a large integer to a friendly text representation. Works best for
    numbers over 1 million. For example, 1000000 becomes '1.0 million', 1200000
    becomes '1.2 million' and '1200000000' becomes '1.2 billion'.
    """
    value = int(value)
    if value < 1000000:
        return value
    if value < 1000000000:
        return '%.1f million' % (value / 1000000.0)
    if value < 1000000000000:
        return '%.1f billion' % (value / 1000000000.0)
    if value < 1000000000000000:
        return '%.1f trillion' % (value / 1000000000000.0)
    return value
register.filter(intword)

def apnumber(value):
    """
    For numbers 1-9, returns the number spelled out. Otherwise, returns the
    number. This follows Associated Press style.
    """
    try:
        value = int(value)
    except ValueError:
        return value
    if not 0 < value < 10:
        return value
    return ('one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')[value-1]
register.filter(apnumber)
