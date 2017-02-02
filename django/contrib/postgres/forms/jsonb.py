import json

from django import forms
from django.utils.translation import ugettext_lazy as _

__all__ = ['JSONField']


class InvalidJSONInput(str):
    pass


class JSONString(str):
    pass


class JSONField(forms.CharField):
    default_error_messages = {
        'invalid': _("'%(value)s' value must be valid JSON."),
    }
    widget = forms.Textarea

    def to_python(self, value):
        if self.disabled:
            return value
        if value in self.empty_values:
            return None
        elif isinstance(value, (list, dict, int, float, JSONString)):
            return value
        try:
            converted = json.loads(value)
        except ValueError:
            raise forms.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )
        if isinstance(converted, str):
            return JSONString(converted)
        else:
            return converted

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
