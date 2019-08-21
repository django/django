import warnings

from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange

from django import forms
from django.core import exceptions
from django.forms.widgets import MultiWidget
from django.utils.deprecation import RemovedInDjango31Warning
from django.utils.translation import gettext_lazy as _

__all__ = [
    'BaseRangeField', 'IntegerRangeField', 'DecimalRangeField',
    'DateTimeRangeField', 'DateRangeField', 'FloatRangeField', 'RangeWidget',
]


class BaseRangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid': _('Enter two valid values.'),
        'bound_ordering': _('The start of the range must not exceed the end of the range.'),
    }

    def __init__(self, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = RangeWidget(self.base_field.widget)
        if 'fields' not in kwargs:
            kwargs['fields'] = [self.base_field(required=False), self.base_field(required=False)]
        kwargs.setdefault('required', False)
        kwargs.setdefault('require_all_fields', False)
        super().__init__(**kwargs)

    def prepare_value(self, value):
        lower_base, upper_base = self.fields
        if isinstance(value, self.range_type):
            return [
                lower_base.prepare_value(value.lower),
                upper_base.prepare_value(value.upper),
            ]
        if value is None:
            return [
                lower_base.prepare_value(None),
                upper_base.prepare_value(None),
            ]
        return value

    def compress(self, values):
        if not values:
            return None
        lower, upper = values
        if lower is not None and upper is not None and lower > upper:
            raise exceptions.ValidationError(
                self.error_messages['bound_ordering'],
                code='bound_ordering',
            )
        try:
            range_value = self.range_type(lower, upper)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
            )
        else:
            return range_value


class IntegerRangeField(BaseRangeField):
    default_error_messages = {'invalid': _('Enter two whole numbers.')}
    base_field = forms.IntegerField
    range_type = NumericRange


class DecimalRangeField(BaseRangeField):
    default_error_messages = {'invalid': _('Enter two numbers.')}
    base_field = forms.DecimalField
    range_type = NumericRange


class FloatRangeField(DecimalRangeField):
    base_field = forms.FloatField

    def __init__(self, **kwargs):
        warnings.warn(
            'FloatRangeField is deprecated in favor of DecimalRangeField.',
            RemovedInDjango31Warning, stacklevel=2,
        )
        super().__init__(**kwargs)


class DateTimeRangeField(BaseRangeField):
    default_error_messages = {'invalid': _('Enter two valid date/times.')}
    base_field = forms.DateTimeField
    range_type = DateTimeTZRange


class DateRangeField(BaseRangeField):
    default_error_messages = {'invalid': _('Enter two valid dates.')}
    base_field = forms.DateField
    range_type = DateRange


class RangeWidget(MultiWidget):
    def __init__(self, base_widget, attrs=None):
        widgets = (base_widget, base_widget)
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return (value.lower, value.upper)
        return (None, None)
