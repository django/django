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
