from django.core import exceptions
from django import forms
from django.utils.translation import ugettext_lazy as _, string_concat

from psycopg2.extras import NumericRange, DateRange, DateTimeTZRange


__all__ = ['IntegerRangeField', 'FloatRangeField', 'DateTimeRangeField', 'DateRangeField']


class BaseRangeField(forms.Field):
    default_error_messages = {
        'invalid': _('Enter two valid values.'),
        'lower_invalid': _('Enter a valid start value: '),
        'upper_invalid': _('Enter a valid end value: '),
        'bound_order': _('The start of the range must not exceed the end of the range.'),
    }

    def __init__(self, **kwargs):
        widget = forms.MultiWidget([self.base_field.widget, self.base_field.widget])
        kwargs.setdefault('widget', widget)
        super(BaseRangeField, self).__init__(**kwargs)

    def prepare_value(self, value):
        if isinstance(value, self.range_type):
            return [value.lower, value.upper]
        if value is None:
            return [None, None]
        return value

    def to_python(self, value):
        base_field = self.base_field()
        try:
            lower, upper = value
        except ValueError:
            raise exceptions.ValidationError(self.error_messages['invalid'],
                    code='invalid')
        try:
            lower = base_field.to_python(lower)
        except exceptions.ValidationError as e:
            message = string_concat(self.error_messages['lower_invalid'], e.message)
            raise exceptions.ValidationError(message, code='lower_invalid')
        try:
            upper = base_field.to_python(upper)
        except exceptions.ValidationError as e:
            message = string_concat(self.error_messages['upper_invalid'], e.message)
            raise exceptions.ValidationError(message, code='upper_invalid')
        if lower is None and upper is None:
            return None
        if lower is not None and upper is not None and lower > upper:
            raise exceptions.ValidationError(self.error_messages['bound_order'],
                    code='bound_order')
        try:
            range_value = self.range_type(lower, upper)
        except TypeError:
            raise exceptions.ValidationError(self.error_messages['invalid'],
                    code='invalid')
        else:
            return range_value


class IntegerRangeField(BaseRangeField):
    base_field = forms.IntegerField
    range_type = NumericRange


class FloatRangeField(BaseRangeField):
    base_field = forms.FloatField
    range_type = NumericRange


class DateTimeRangeField(BaseRangeField):
    base_field = forms.DateTimeField
    range_type = DateTimeTZRange


class DateRangeField(BaseRangeField):
    base_field = forms.DateField
    range_type = DateRange
