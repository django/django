from django.contrib.postgres.validators import ArrayMinLengthValidator, ArrayMaxLengthValidator
from django.core.exceptions import ValidationError
from django import forms
from django.utils.translation import string_concat, ugettext_lazy as _


class SimpleArrayField(forms.CharField):
    default_error_messages = {
        'item_invalid': _('Item %(nth)s in the array did not validate: '),
    }

    def __init__(self, base_field, delimiter=',', max_length=None, min_length=None, *args, **kwargs):
        self.base_field = base_field
        self.delimiter = delimiter
        super(SimpleArrayField, self).__init__(*args, **kwargs)
        if min_length is not None:
            self.min_length = min_length
            self.validators.append(ArrayMinLengthValidator(int(min_length)))
        if max_length is not None:
            self.max_length = max_length
            self.validators.append(ArrayMaxLengthValidator(int(max_length)))

    def prepare_value(self, value):
        if isinstance(value, list):
            return self.delimiter.join(str(self.base_field.prepare_value(v)) for v in value)
        return value

    def to_python(self, value):
        if value:
            items = value.split(self.delimiter)
        else:
            items = []
        errors = []
        values = []
        for i, item in enumerate(items):
            try:
                values.append(self.base_field.to_python(item))
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_invalid'], error.message),
                        code='item_invalid',
                        params={'nth': i},
                    ))
        if errors:
            raise ValidationError(errors)
        return values

    def validate(self, value):
        super(SimpleArrayField, self).validate(value)
        errors = []
        for i, item in enumerate(value):
            try:
                self.base_field.validate(item)
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_invalid'], error.message),
                        code='item_invalid',
                        params={'nth': i},
                    ))
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value):
        super(SimpleArrayField, self).run_validators(value)
        errors = []
        for i, item in enumerate(value):
            try:
                self.base_field.run_validators(item)
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_invalid'], error.message),
                        code='item_invalid',
                        params={'nth': i},
                    ))
        if errors:
            raise ValidationError(errors)


class SplitArrayWidget(forms.MultiWidget):

    def __init__(self, widget, size, max_allowable_size=None, **kwargs):
        self.widget = widget
        self.size = size
        self.max_allowable_size = max_allowable_size or size
        widgets = [widget] * size
        super(SplitArrayWidget, self).__init__(widgets, **kwargs)

    def value_from_datadict(self, data, files, name):
        return [self.widget.value_from_datadict(data, files, name + '_%s' % i) for i in range(self.max_allowable_size)]

    def decompress(self, value):
        return value or []


class SplitArrayField(forms.MultiValueField):

    def __init__(self, base_field, size, remove_trailing_nulls=False, max_allowable_size=None, **kwargs):
        self.base_field = base_field
        self.size = size
        fields = (base_field,) * size
        if max_allowable_size is not None and max_allowable_size < size:
            raise ValueError('Max allowable size of a SplitArrayField must be larger than the initial size.')
        self.max_allowable_size = max_allowable_size
        self.remove_trailing_nulls = remove_trailing_nulls
        if remove_trailing_nulls:
            # required=True doesn't make sense if we are allowing nulls
            kwargs['required'] = False
        widget = SplitArrayWidget(widget=base_field.widget, size=size, max_allowable_size=max_allowable_size)
        kwargs.setdefault('widget', widget)
        super(SplitArrayField, self).__init__(fields, **kwargs)

    def compress(self, data_list):
        return data_list

    def clean(self, value):
        if self.max_allowable_size != self.size and len(value) > len(self.fields):
            # Extend the field list if we have max_allowable_size > self.size
            self.fields = (self.base_field,) * len(value)
        out = super(SplitArrayField, self).clean(value)
        if self.max_allowable_size != self.size and len(self.fields) > self.size:
            self.fields = (self.base_field,) * self.size
        if self.remove_trailing_nulls:
            null_index = None
            for i, value in reversed(list(enumerate(out))):
                if value in self.empty_values:
                    null_index = i
                else:
                    break
            if null_index:
                return out[:null_index]
        return out
