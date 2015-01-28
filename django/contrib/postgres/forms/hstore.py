import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.translation import ugettext_lazy as _

__all__ = ['HStoreField']


class HStoreField(forms.CharField):
    """A field for HStore data which accepts JSON input."""
    widget = forms.Textarea
    default_error_messages = {
        'invalid_json': _('Could not load JSON data.'),
    }

    def prepare_value(self, value):
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def to_python(self, value):
        if not value:
            return {}
        try:
            value = json.loads(value)
        except ValueError:
            raise ValidationError(
                self.error_messages['invalid_json'],
                code='invalid_json',
            )
        # Cast everything to strings for ease.
        for key, val in value.items():
            value[key] = six.text_type(val)
        return value
