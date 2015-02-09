"""
Extra HTML Widget classes
"""
from __future__ import unicode_literals

import datetime
import re

from django.conf import settings
from django.forms.widgets import Select, Widget
from django.utils import datetime_safe, six
from django.utils.dates import MONTHS
from django.utils.encoding import force_str
from django.utils.formats import get_format
from django.utils.safestring import mark_safe

__all__ = ('SelectDateWidget',)

RE_DATE = re.compile(r'(\d{4})-(\d\d?)-(\d\d?)$')


def _parse_date_fmt():
    fmt = get_format('DATE_FORMAT')
    escaped = False
    for char in fmt:
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char in 'Yy':
            yield 'year'
        elif char in 'bEFMmNn':
            yield 'month'
        elif char in 'dj':
            yield 'day'


class SelectDateWidget(Widget):
    """
    A Widget that splits date input into three <select> boxes.

    This also serves as an example of a Widget that has more than one HTML
    element and hence implements value_from_datadict.
    """
    none_value = (0, '---')
    month_field = '%s_month'
    day_field = '%s_day'
    year_field = '%s_year'

    def __init__(self, attrs=None, years=None, months=None, empty_label=None):
        self.attrs = attrs or {}

        # Optional list or tuple of years to use in the "year" select box.
        if years:
            self.years = years
        else:
            this_year = datetime.date.today().year
            self.years = range(this_year, this_year + 10)

        # Optional dict of months to use in the "month" select box.
        if months:
            self.months = months
        else:
            self.months = MONTHS

        # Optional string, list, or tuple to use as empty_label.
        if isinstance(empty_label, (list, tuple)):
            if not len(empty_label) == 3:
                raise ValueError('empty_label list/tuple must have 3 elements.')

            self.year_none_value = (0, empty_label[0])
            self.month_none_value = (0, empty_label[1])
            self.day_none_value = (0, empty_label[2])
        else:
            if empty_label is not None:
                self.none_value = (0, empty_label)

            self.year_none_value = self.none_value
            self.month_none_value = self.none_value
            self.day_none_value = self.none_value

    def render(self, name, value, attrs=None):
        try:
            year_val, month_val, day_val = value.year, value.month, value.day
        except AttributeError:
            year_val = month_val = day_val = None
            if isinstance(value, six.string_types):
                if settings.USE_L10N:
                    try:
                        input_format = get_format('DATE_INPUT_FORMATS')[0]
                        v = datetime.datetime.strptime(force_str(value), input_format)
                        year_val, month_val, day_val = v.year, v.month, v.day
                    except ValueError:
                        pass
                else:
                    match = RE_DATE.match(value)
                    if match:
                        year_val, month_val, day_val = [int(v) for v in match.groups()]
        html = {}
        choices = [(i, i) for i in self.years]
        html['year'] = self.create_select(name, self.year_field, value, year_val, choices, self.year_none_value)
        choices = list(six.iteritems(self.months))
        html['month'] = self.create_select(name, self.month_field, value, month_val, choices, self.month_none_value)
        choices = [(i, i) for i in range(1, 32)]
        html['day'] = self.create_select(name, self.day_field, value, day_val, choices, self.day_none_value)

        output = []
        for field in _parse_date_fmt():
            output.append(html[field])
        return mark_safe('\n'.join(output))

    def id_for_label(self, id_):
        for first_select in _parse_date_fmt():
            return '%s_%s' % (id_, first_select)
        else:
            return '%s_month' % id_

    def value_from_datadict(self, data, files, name):
        y = data.get(self.year_field % name)
        m = data.get(self.month_field % name)
        d = data.get(self.day_field % name)
        if y == m == d == "0":
            return None
        if y and m and d:
            if settings.USE_L10N:
                input_format = get_format('DATE_INPUT_FORMATS')[0]
                try:
                    date_value = datetime.date(int(y), int(m), int(d))
                except ValueError:
                    return '%s-%s-%s' % (y, m, d)
                else:
                    date_value = datetime_safe.new_date(date_value)
                    return date_value.strftime(input_format)
            else:
                return '%s-%s-%s' % (y, m, d)
        return data.get(name, None)

    def create_select(self, name, field, value, val, choices, none_value):
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name
        if not self.is_required:
            choices.insert(0, none_value)
        local_attrs = self.build_attrs(id=field % id_)
        s = Select(choices=choices)
        select_html = s.render(field % name, val, local_attrs)
        return select_html
