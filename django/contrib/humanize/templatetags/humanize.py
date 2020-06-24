import re
from datetime import date, datetime
from decimal import Decimal

from django import template
from django.template import defaultfilters
from django.utils.formats import number_format
from django.utils.safestring import mark_safe
from django.utils.timezone import is_aware, utc
from django.utils.translation import (
    gettext as _, gettext_lazy, ngettext, ngettext_lazy, npgettext_lazy,
    pgettext, round_away_from_one,
)

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
    if value % 100 in (11, 12, 13):
        # Translators: Ordinal format for 11 (11th), 12 (12th), and 13 (13th).
        value = pgettext('ordinal 11, 12, 13', '{}th').format(value)
    else:
        templates = (
            # Translators: Ordinal format when value ends with 0, e.g. 80th.
            pgettext('ordinal 0', '{}th'),
            # Translators: Ordinal format when value ends with 1, e.g. 81st, except 11.
            pgettext('ordinal 1', '{}st'),
            # Translators: Ordinal format when value ends with 2, e.g. 82nd, except 12.
            pgettext('ordinal 2', '{}nd'),
            # Translators: Ordinal format when value ends with 3, e.g. 83th, except 13.
            pgettext('ordinal 3', '{}rd'),
            # Translators: Ordinal format when value ends with 4, e.g. 84th.
            pgettext('ordinal 4', '{}th'),
            # Translators: Ordinal format when value ends with 5, e.g. 85th.
            pgettext('ordinal 5', '{}th'),
            # Translators: Ordinal format when value ends with 6, e.g. 86th.
            pgettext('ordinal 6', '{}th'),
            # Translators: Ordinal format when value ends with 7, e.g. 87th.
            pgettext('ordinal 7', '{}th'),
            # Translators: Ordinal format when value ends with 8, e.g. 88th.
            pgettext('ordinal 8', '{}th'),
            # Translators: Ordinal format when value ends with 9, e.g. 89th.
            pgettext('ordinal 9', '{}th'),
        )
        value = templates[value % 10].format(value)
    # Mark value safe so i18n does not break with <sup> or <sub> see #19988
    return mark_safe(value)


@register.filter(is_safe=True)
def intcomma(value, use_l10n=True):
    """
    Convert an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    if use_l10n:
        try:
            if not isinstance(value, (float, Decimal)):
                value = int(value)
        except (TypeError, ValueError):
            return intcomma(value, False)
        else:
            return number_format(value, use_l10n=True, force_grouping=True)
    orig = str(value)
    new = re.sub(r"^(-?\d+)(\d{3})", r'\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new, use_l10n)


# A tuple of standard large number to their converters
intword_converters = (
    (6, lambda number: ngettext('%(value)s million', '%(value)s million', number)),
    (9, lambda number: ngettext('%(value)s billion', '%(value)s billion', number)),
    (12, lambda number: ngettext('%(value)s trillion', '%(value)s trillion', number)),
    (15, lambda number: ngettext('%(value)s quadrillion', '%(value)s quadrillion', number)),
    (18, lambda number: ngettext('%(value)s quintillion', '%(value)s quintillion', number)),
    (21, lambda number: ngettext('%(value)s sextillion', '%(value)s sextillion', number)),
    (24, lambda number: ngettext('%(value)s septillion', '%(value)s septillion', number)),
    (27, lambda number: ngettext('%(value)s octillion', '%(value)s octillion', number)),
    (30, lambda number: ngettext('%(value)s nonillion', '%(value)s nonillion', number)),
    (33, lambda number: ngettext('%(value)s decillion', '%(value)s decillion', number)),
    (100, lambda number: ngettext('%(value)s googol', '%(value)s googol', number)),
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

    abs_value = abs(value)
    if abs_value < 1000000:
        return value

    for exponent, converter in intword_converters:
        large_number = 10 ** exponent
        if abs_value < large_number * 1000:
            new_value = value / large_number
            rounded_value = round_away_from_one(new_value)
            return converter(abs(rounded_value)) % {
                'value': defaultfilters.floatformat(new_value, 1),
            }
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
    tzinfo = getattr(value, 'tzinfo', None)
    try:
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't a date object
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
    return NaturalTimeFormatter.string_for(value)


class NaturalTimeFormatter:
    time_strings = {
        # Translators: delta will contain a string like '2 months' or '1 month, 2 weeks'
        'past-day': gettext_lazy('%(delta)s ago'),
        # Translators: please keep a non-breaking space (U+00A0) between count
        # and time unit.
        'past-hour': ngettext_lazy('an hour ago', '%(count)s hours ago', 'count'),
        # Translators: please keep a non-breaking space (U+00A0) between count
        # and time unit.
        'past-minute': ngettext_lazy('a minute ago', '%(count)s minutes ago', 'count'),
        # Translators: please keep a non-breaking space (U+00A0) between count
        # and time unit.
        'past-second': ngettext_lazy('a second ago', '%(count)s seconds ago', 'count'),
        'now': gettext_lazy('now'),
        # Translators: please keep a non-breaking space (U+00A0) between count
        # and time unit.
        'future-second': ngettext_lazy('a second from now', '%(count)s seconds from now', 'count'),
        # Translators: please keep a non-breaking space (U+00A0) between count
        # and time unit.
        'future-minute': ngettext_lazy('a minute from now', '%(count)s minutes from now', 'count'),
        # Translators: please keep a non-breaking space (U+00A0) between count
        # and time unit.
        'future-hour': ngettext_lazy('an hour from now', '%(count)s hours from now', 'count'),
        # Translators: delta will contain a string like '2 months' or '1 month, 2 weeks'
        'future-day': gettext_lazy('%(delta)s from now'),
    }
    past_substrings = {
        # Translators: 'naturaltime-past' strings will be included in '%(delta)s ago'
        'year': npgettext_lazy('naturaltime-past', '%d year', '%d years'),
        'month': npgettext_lazy('naturaltime-past', '%d month', '%d months'),
        'week': npgettext_lazy('naturaltime-past', '%d week', '%d weeks'),
        'day': npgettext_lazy('naturaltime-past', '%d day', '%d days'),
        'hour': npgettext_lazy('naturaltime-past', '%d hour', '%d hours'),
        'minute': npgettext_lazy('naturaltime-past', '%d minute', '%d minutes'),
    }
    future_substrings = {
        # Translators: 'naturaltime-future' strings will be included in '%(delta)s from now'
        'year': npgettext_lazy('naturaltime-future', '%d year', '%d years'),
        'month': npgettext_lazy('naturaltime-future', '%d month', '%d months'),
        'week': npgettext_lazy('naturaltime-future', '%d week', '%d weeks'),
        'day': npgettext_lazy('naturaltime-future', '%d day', '%d days'),
        'hour': npgettext_lazy('naturaltime-future', '%d hour', '%d hours'),
        'minute': npgettext_lazy('naturaltime-future', '%d minute', '%d minutes'),
    }

    @classmethod
    def string_for(cls, value):
        if not isinstance(value, date):  # datetime is a subclass of date
            return value

        now = datetime.now(utc if is_aware(value) else None)
        if value < now:
            delta = now - value
            if delta.days != 0:
                return cls.time_strings['past-day'] % {
                    'delta': defaultfilters.timesince(value, now, time_strings=cls.past_substrings),
                }
            elif delta.seconds == 0:
                return cls.time_strings['now']
            elif delta.seconds < 60:
                return cls.time_strings['past-second'] % {'count': delta.seconds}
            elif delta.seconds // 60 < 60:
                count = delta.seconds // 60
                return cls.time_strings['past-minute'] % {'count': count}
            else:
                count = delta.seconds // 60 // 60
                return cls.time_strings['past-hour'] % {'count': count}
        else:
            delta = value - now
            if delta.days != 0:
                return cls.time_strings['future-day'] % {
                    'delta': defaultfilters.timeuntil(value, now, time_strings=cls.future_substrings),
                }
            elif delta.seconds == 0:
                return cls.time_strings['now']
            elif delta.seconds < 60:
                return cls.time_strings['future-second'] % {'count': delta.seconds}
            elif delta.seconds // 60 < 60:
                count = delta.seconds // 60
                return cls.time_strings['future-minute'] % {'count': count}
            else:
                count = delta.seconds // 60 // 60
                return cls.time_strings['future-hour'] % {'count': count}
