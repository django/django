import re
from datetime import date, datetime, timedelta

from django import template
from django.conf import settings
from django.template import defaultfilters
from django.utils.datetime_safe import datetime, date
from django.utils.encoding import force_unicode
from django.utils.formats import number_format
from django.utils.translation import pgettext, ungettext, ugettext as _
from django.utils.tzinfo import LocalTimezone


register = template.Library()

def ordinal(value):
    """
    Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    t = (_('th'), _('st'), _('nd'), _('rd'), _('th'), _('th'), _('th'), _('th'), _('th'), _('th'))
    if value % 100 in (11, 12, 13): # special case
        return u"%d%s" % (value, t[0])
    return u'%d%s' % (value, t[value % 10])
ordinal.is_safe = True
register.filter(ordinal)

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
            return number_format(value)
    orig = force_unicode(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new, use_l10n)
intcomma.is_safe = True
register.filter(intcomma)

def intword(value):
    """
    Converts a large integer to a friendly text representation. Works best for
    numbers over 1 million. For example, 1000000 becomes '1.0 million', 1200000
    becomes '1.2 million' and '1200000000' becomes '1.2 billion'.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    if value < 1000000:
        return value

    def _check_for_i18n(value, float_formatted, string_formatted):
        """
        Use the i18n enabled defaultfilters.floatformat if possible
        """
        if settings.USE_L10N:
            return defaultfilters.floatformat(value, 1), string_formatted
        return value, float_formatted

    if value < 1000000000:
        new_value = value / 1000000.0
        new_value, value_string = _check_for_i18n(new_value,
            ungettext('%(value).1f million', '%(value).1f million', new_value),
            ungettext('%(value)s million', '%(value)s million', new_value))
        return value_string % {'value': new_value}
    if value < 1000000000000:
        new_value = value / 1000000000.0
        new_value, value_string = _check_for_i18n(new_value,
            ungettext('%(value).1f billion', '%(value).1f billion', new_value),
            ungettext('%(value)s billion', '%(value)s billion', new_value))
        return value_string % {'value': new_value}
    if value < 1000000000000000:
        new_value = value / 1000000000000.0
        new_value, value_string = _check_for_i18n(new_value,
            ungettext('%(value).1f trillion', '%(value).1f trillion', new_value),
            ungettext('%(value)s trillion', '%(value)s trillion', new_value))
        return value_string % {'value': new_value}
    return value
intword.is_safe = False
register.filter(intword)

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
apnumber.is_safe = True
register.filter(apnumber)

@register.filter
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
    today = datetime.now(tzinfo).replace(microsecond=0, second=0, minute=0, hour=0)
    delta = value - today.date()
    if delta.days == 0:
        return _(u'today')
    elif delta.days == 1:
        return _(u'tomorrow')
    elif delta.days == -1:
        return _(u'yesterday')
    return defaultfilters.date(value, arg)

@register.filter
def naturaltime(value):
    """
    For date and time values shows how many seconds, minutes or hours ago
    compared to current timestamp returns representing string.
    """
    try:
        value = datetime(value.year, value.month, value.day, value.hour, value.minute, value.second)
    except AttributeError:
        return value
    except ValueError:
        return value

    if getattr(value, 'tzinfo', None):
        now = datetime.now(LocalTimezone(value))
    else:
        now = datetime.now()
    now = now - timedelta(0, 0, now.microsecond)
    if value < now:
        delta = now - value
        if delta.days != 0:
            return pgettext(
                'naturaltime', '%(delta)s ago'
            ) % {'delta': defaultfilters.timesince(value)}
        elif delta.seconds == 0:
            return _(u'now')
        elif delta.seconds < 60:
            return ungettext(
                u'a second ago', u'%(count)s seconds ago', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds / 60 < 60:
            count = delta.seconds / 60
            return ungettext(
                u'a minute ago', u'%(count)s minutes ago', count
            ) % {'count': count}
        else:
            count = delta.seconds / 60 / 60
            return ungettext(
                u'an hour ago', u'%(count)s hours ago', count
            ) % {'count': count}
    else:
        delta = value - now
        if delta.days != 0:
            return pgettext(
                'naturaltime', '%(delta)s from now'
            ) % {'delta': defaultfilters.timeuntil(value)}
        elif delta.seconds == 0:
            return _(u'now')
        elif delta.seconds < 60:
            return ungettext(
                u'a second from now', u'%(count)s seconds from now', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds / 60 < 60:
            count = delta.seconds / 60
            return ungettext(
                u'a minute from now', u'%(count)s minutes from now', count
            ) % {'count': count}
        else:
            count = delta.seconds / 60 / 60
            return ungettext(
                u'an hour from now', u'%(count)s hours from now', count
            ) % {'count': count}
