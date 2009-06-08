import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

def validate_integer(value):
    try:
        int(value)
    except (ValueError, TypeError), e:
        raise ValidationError('')

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9]+(?:-*[A-Z0-9]+)*\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

def validate_email(value):
    if not email_re.search(smart_unicode(value)):
        raise ValidationError(_(u'Enter a valid e-mail address.'))

class ComplexValidator(object):
    def get_value(self, name, all_values, obj):
        assert all_values or obj, "Either all_values or obj must be supplied"

        if all_values:
            return all_values.get(name, None)
        if obj:
            return getattr(obj, name, None)
        

    def __call__(self, value, all_values={}, obj=None):
        raise NotImplementedError()

class RequiredIfOtherFieldBlank(ComplexValidator):
    def __init__(self, other_field):
        self.other_field = other_field

    def __call__(self, value, all_values={}, obj=None):
        if self.get_value(self.other_field, all_values, obj) in EMPTY_VALUES:
            if value in EMPTY_VALUES:
                raise ValidationError('This field is required if %s is blank.' % self.other_field)
