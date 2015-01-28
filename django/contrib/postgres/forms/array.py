import copy

from django import forms
from django.contrib.postgres.validators import (
    ArrayMaxLengthValidator, ArrayMinLengthValidator,
)
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.safestring import mark_safe
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
            return self.delimiter.join(six.text_type(self.base_field.prepare_value(v)) for v in value)
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


class SplitArrayWidget(forms.Widget):

    def __init__(self, widget, size, **kwargs):
        self.widget = widget() if isinstance(widget, type) else widget
        self.size = size
        super(SplitArrayWidget, self).__init__(**kwargs)

    @property
    def is_hidden(self):
        return self.widget.is_hidden

    def value_from_datadict(self, data, files, name):
        return [self.widget.value_from_datadict(data, files, '%s_%s' % (name, index))
                for index in range(self.size)]

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_

    def render(self, name, value, attrs=None):
        if self.is_localized:
            self.widget.is_localized = self.is_localized
        value = value or []
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i in range(max(len(value), self.size)):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(self.widget.render(name + '_%s' % i, widget_value, final_attrs))
        return mark_safe(self.format_output(output))

    def format_output(self, rendered_widgets):
        return ''.join(rendered_widgets)

    @property
    def media(self):
        return self.widget.media

    def __deepcopy__(self, memo):
        obj = super(SplitArrayWidget, self).__deepcopy__(memo)
        obj.widget = copy.deepcopy(self.widget)
        return obj

    @property
    def needs_multipart_form(self):
        return self.widget.needs_multipart_form


class SplitArrayField(forms.Field):
    default_error_messages = {
        'item_invalid': _('Item %(nth)s in the array did not validate: '),
    }

    def __init__(self, base_field, size, remove_trailing_nulls=False, **kwargs):
        self.base_field = base_field
        self.size = size
        self.remove_trailing_nulls = remove_trailing_nulls
        widget = SplitArrayWidget(widget=base_field.widget, size=size)
        kwargs.setdefault('widget', widget)
        super(SplitArrayField, self).__init__(**kwargs)

    def clean(self, value):
        cleaned_data = []
        errors = []
        if not any(value) and self.required:
            raise ValidationError(self.error_messages['required'])
        max_size = max(self.size, len(value))
        for i in range(max_size):
            item = value[i]
            try:
                cleaned_data.append(self.base_field.clean(item))
                errors.append(None)
            except ValidationError as error:
                errors.append(ValidationError(
                    string_concat(self.error_messages['item_invalid'], error.message),
                    code='item_invalid',
                    params={'nth': i},
                ))
                cleaned_data.append(None)
        if self.remove_trailing_nulls:
            null_index = None
            for i, value in reversed(list(enumerate(cleaned_data))):
                if value in self.base_field.empty_values:
                    null_index = i
                else:
                    break
            if null_index:
                cleaned_data = cleaned_data[:null_index]
                errors = errors[:null_index]
        errors = list(filter(None, errors))
        if errors:
            raise ValidationError(errors)
        return cleaned_data
