from __future__ import unicode_literals
import re
from datetime import date, datetime

from django import template
from django.conf import settings
from django.template import defaultfilters
from django.utils.encoding import force_text
from django.utils.formats import number_format
from django.utils.translation import pgettext, ungettext, ugettext as _
from django.utils.timezone import is_aware, utc

register = template.Library()

@register.filter(is_safe=True)
def ordinal(value):
    """
    Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    suffixes = (_('th'), _('st'), _('nd'), _('rd'), _('th'), _('th'), _('th'), _('th'), _('th'), _('th'))
    if value % 100 in (11, 12, 13): # special case
        return "%d%s" % (value, suffixes[0])
    return "%d%s" % (value, suffixes[value % 10])

@register.filter(is_safe=True)
def intcomma(value, use_l10n=True):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    if settings.USE_L10N and use_l10n:
        try:
            if not isinstance(value, float):
                value = int(value)
        except (TypeError, ValueError):
            return intcomma(value, False)
        else:
            return number_format(value, force_grouping=True)
    orig = force_text(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new, use_l10n)

# A tuple of standard large number to their converters
class Converter(object):
    def __init__(self, precision=1, word_abr_symbol=0, word_abr_list=None):
        self.precision = str(precision)
        if word_abr_list == None:
            word_abr_list = (
                             (' thousand', 'K','K',),
                             (' million', 'M','M',),
                             (' billion', 'B','G',),
                             (' trillion', 'T','T',),
                             (' quadrillion', 'Qd','P',),
                             (' quintillion', 'Qt','E',),
                             (' sextillion', 'Sx','Z'),
                             (' septillion', 'Sp','Y',),
                             (' octillion', 'O','',),
                             (' nonillion', 'N',''),
                             (' decillion', 'D',''),
                             (' googol', 'G',''),
                             )
        self.intword_converters = []
        for k, converter in enumerate(word_abr_list):
            self.intword_converters.append(self._ungettext(3*(k+1), converter[word_abr_symbol]))
        self.len_converters = len(self.intword_converters)
    
    def _ungettext(self, exponent, arg):
        return (exponent, lambda number: (
                ungettext('%(value).{0}f{1}'.format(self.precision, arg), '%(value).{0}f{1}'.format(self.precision, arg), number),
                ungettext('%(value)s{0}'.format(arg), '%(value)s{0}'.format(arg), number),
            ))
    def __iter__(self):
        self.current = 0
        return self

    def next(self):
        if self.current == self.len_converters:
            self.current = 0
            raise StopIteration
        else:
            r = self.intword_converters[self.current]
            self.current += 1
            return r


def _intword(value, precision=1, max_num=1000000, word_abr_symbol=0, converter=Converter, **kwargs):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value

    if value < max_num:
        return value

    def _check_for_i18n(value, float_formatted, string_formatted):
        """
        Use the i18n enabled defaultfilters.floatformat if possible
        """
        if settings.USE_L10N:
            value = defaultfilters.floatformat(value, precision)
            template = string_formatted
        else:
            template = float_formatted
        return template % {'value': value}
    intword_converters = converter(precision, word_abr_symbol, **kwargs)#.intword_converters
    for exponent, converters in intword_converters:
        large_number = 10 ** exponent
        if value < large_number * 1000:
            new_value = value / float(large_number)
            return _check_for_i18n(new_value, *converters(new_value))
    return value

def intword_internal(value, precision=1, max_num=1000000, word_abr_symbol=0, converter=Converter, **kwargs):
    return _intword(value, precision, word_abr_symbol, max_num, converter, **kwargs)

@register.filter(is_safe=False)
def intword(value, precision=1):
    return _intword(value, precision, word_abr_symbol=0)

@register.filter(is_safe=False)
def intabr(value, precision=1):
    return _intword(value, precision, word_abr_symbol=1)

@register.filter(is_safe=True)
def apnumber(value):
    """
    For numbers 1-9, returns the number spelled out. Otherwise, returns the
    number. This follows Associated Press style.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    if not 0 < value < 10:
        return value
    return (_('one'), _('two'), _('three'), _('four'), _('five'), _('six'), _('seven'), _('eight'), _('nine'))[value-1]

# Perform the comparison in the default time zone when USE_TZ = True
# (unless a specific time zone has been applied with the |timezone filter).
@register.filter(expects_localtime=True)
def naturalday(value, arg=None):
    """
    For date values that are tomorrow, today or yesterday compared to
    present day returns representing string. Otherwise, returns a string
    formatted according to settings.DATE_FORMAT.
    """
    try:
        tzinfo = getattr(value, 'tzinfo', None)
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't a date object
        return value
    except ValueError:
        # Date arguments out of range
        return value
    today = datetime.now(tzinfo).date()
    delta = value - today
    if delta.days == 0:
        return _('today')
    elif delta.days == 1:
        return _('tomorrow')
    elif delta.days == -1:
        return _('yesterday')
    return defaultfilters.date(value, arg)

# This filter doesn't require expects_localtime=True because it deals properly
# with both naive and aware datetimes. Therefore avoid the cost of conversion.
@register.filter
def naturaltime(value):
    """
    For date and time values shows how many seconds, minutes or hours ago
    compared to current timestamp returns representing string.
    """
    if not isinstance(value, date): # datetime is a subclass of date
        return value

    now = datetime.now(utc if is_aware(value) else None)
    if value < now:
        delta = now - value
        if delta.days != 0:
            return pgettext(
                'naturaltime', '%(delta)s ago'
            ) % {'delta': defaultfilters.timesince(value, now)}
        elif delta.seconds == 0:
            return _('now')
        elif delta.seconds < 60:
            return ungettext(
                'a second ago', '%(count)s seconds ago', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds // 60 < 60:
            count = delta.seconds // 60
            return ungettext(
                'a minute ago', '%(count)s minutes ago', count
            ) % {'count': count}
        else:
            count = delta.seconds // 60 // 60
            return ungettext(
                'an hour ago', '%(count)s hours ago', count
            ) % {'count': count}
    else:
        delta = value - now
        if delta.days != 0:
            return pgettext(
                'naturaltime', '%(delta)s from now'
            ) % {'delta': defaultfilters.timeuntil(value, now)}
        elif delta.seconds == 0:
            return _('now')
        elif delta.seconds < 60:
            return ungettext(
                'a second from now', '%(count)s seconds from now', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds // 60 < 60:
            count = delta.seconds // 60
            return ungettext(
                'a minute from now', '%(count)s minutes from now', count
            ) % {'count': count}
        else:
            count = delta.seconds // 60 // 60
            return ungettext(
                'an hour from now', '%(count)s hours from now', count
            ) % {'count': count}
