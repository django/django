import json

from django import forms
from django.utils import six
from django.utils.translation import ugettext_lazy as _

__all__ = ['JSONField']


class InvalidJSONInput(six.text_type):
    pass


class JSONField(forms.CharField):
    default_error_messages = {
        'invalid': _("'%(value)s' value must be valid JSON."),
    }

    def __init__(self, **kwargs):
        kwargs.setdefault('widget', forms.Textarea)
        super(JSONField, self).__init__(**kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return json.loads(value)
        except ValueError:
            raise forms.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def bound_data(self, data, initial):
        if self.disabled:
            return initial
        try:
            return json.loads(data)
        except ValueError:
            return InvalidJSONInput(data)

    def prepare_value(self, value):
        if isinstance(value, InvalidJSONInput):
            return value
        return json.dumps(value)
