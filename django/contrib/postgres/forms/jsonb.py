import json

from django import forms
from django.utils.translation import ugettext_lazy as _

__all__ = ['JSONField']


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

    def prepare_value(self, value):
        return json.dumps(value)
