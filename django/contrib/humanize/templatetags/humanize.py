import re
from datetime import date, datetime
from decimal import Decimal

from django import template
from django.conf import settings
from django.template import defaultfilters
from django.utils.formats import number_format
from django.utils.safestring import mark_safe
from django.utils.timezone import is_aware, utc
from django.utils.translation import gettext as _, ngettext, pgettext

register = template.Library()


@register.filter(is_safe=True)
def ordinal(value):
    """
    Convert an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    suffixes = (_('th'), _('st'), _('nd'), _('rd'), _('th'), _('th'), _('th'), _('th'), _('th'), _('th'))
    if value % 100 in (11, 12, 13):  # special case
        return mark_safe("%d%s" % (value, suffixes[0]))
    # Mark value safe so i18n does not break with <sup> or <sub> see #19988
    return mark_safe("%d%s" % (value, suffixes[value % 10]))


@register.filter(is_safe=True)
def intcomma(value, use_l10n=True):
    """
    Convert an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    if settings.USE_L10N and use_l10n:
        try:
            if not isinstance(value, (float, Decimal)):
                value = int(value)
        except (TypeError, ValueError):
            return intcomma(value, False)
        else:
            return number_format(value, force_grouping=True)
    orig = str(value)
    new = re.sub(r"^(-?\d+)(\d{3})", r'\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new, use_l10n)


# A tuple of standard large number to their converters
intword_converters = (
    (6, lambda number: (
        ngettext('%(value).1f million', '%(value).1f million', number),
        ngettext('%(value)s million', '%(value)s million', number),
    )),
    (9, lambda number: (
        ngettext('%(value).1f billion', '%(value).1f billion', number),
        ngettext('%(value)s billion', '%(value)s billion', number),
    )),
    (12, lambda number: (
        ngettext('%(value).1f trillion', '%(value).1f trillion', number),
        ngettext('%(value)s trillion', '%(value)s trillion', number),
    )),
    (15, lambda number: (
        ngettext('%(value).1f quadrillion', '%(value).1f quadrillion', number),
        ngettext('%(value)s quadrillion', '%(value)s quadrillion', number),
    )),
    (18, lambda number: (
        ngettext('%(value).1f quintillion', '%(value).1f quintillion', number),
        ngettext('%(value)s quintillion', '%(value)s quintillion', number),
    )),
    (21, lambda number: (
        ngettext('%(value).1f sextillion', '%(value).1f sextillion', number),
        ngettext('%(value)s sextillion', '%(value)s sextillion', number),
    )),
    (24, lambda number: (
        ngettext('%(value).1f septillion', '%(value).1f septillion', number),
        ngettext('%(value)s septillion', '%(value)s septillion', number),
    )),
    (27, lambda number: (
        ngettext('%(value).1f octillion', '%(value).1f octillion', number),
        ngettext('%(value)s octillion', '%(value)s octillion', number),
    )),
    (30, lambda number: (
        ngettext('%(value).1f nonillion', '%(value).1f nonillion', number),
        ngettext('%(value)s nonillion', '%(value)s nonillion', number),
    )),
    (33, lambda number: (
        ngettext('%(value).1f decillion', '%(value).1f decillion', number),
        ngettext('%(value)s decillion', '%(value)s decillion', number),
    )),
    (100, lambda number: (
        ngettext('%(value).1f googol', '%(value).1f googol', number),
        ngettext('%(value)s googol', '%(value)s googol', number),
    )),
)


@register.filter(is_safe=False)
def intword(value):
    """
    Convert a large integer to a friendly text representation. Works best
    for numbers over 1 million. For example, 1000000 becomes '1.0 million',
    1200000 becomes '1.2 million' and '1200000000' becomes '1.2 billion'.
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
            value = defaultfilters.floatformat(value, 1)
            template = string_formatted
        else:
            template = float_formatted
        return template % {'value': value}

    for exponent, converters in intword_converters:
        large_number = 10 ** exponent
        if value < large_number * 1000:
            new_value = value / float(large_number)
            return _check_for_i18n(new_value, *converters(new_value))
    return value


@register.filter(is_safe=True)
def apnumber(value):
    """
    For numbers 1-9, return the number spelled out. Otherwise, return the
    number. This follows Associated Press style.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    if not 0 < value < 10:
        return value
    return (_('one'), _('two'), _('three'), _('four'), _('five'),
            _('six'), _('seven'), _('eight'), _('nine'))[value - 1]


# Perform the comparison in the default time zone when USE_TZ = True
# (unless a specific time zone has been applied with the |timezone filter).
@register.filter(expects_localtime=True)
def naturalday(value, arg=None):
    """
    For date values that are tomorrow, today or yesterday compared to
    present day return representing string. Otherwise, return a string
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
    For date and time values show how many seconds, minutes, or hours ago
    compared to current timestamp return representing string.
    """
    if not isinstance(value, date):  # datetime is a subclass of date
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
            return ngettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a second ago', '%(count)s seconds ago', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds // 60 < 60:
            count = delta.seconds // 60
            return ngettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a minute ago', '%(count)s minutes ago', count
            ) % {'count': count}
        else:
            count = delta.seconds // 60 // 60
            return ngettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'an hour ago', '%(count)s hours ago', count
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
            return ngettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a second from now', '%(count)s seconds from now', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds // 60 < 60:
            count = delta.seconds // 60
            return ngettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a minute from now', '%(count)s minutes from now', count
            ) % {'count': count}
        else:
            count = delta.seconds // 60 // 60
            return ngettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'an hour from now', '%(count)s hours from now', count
            ) % {'count': count}
