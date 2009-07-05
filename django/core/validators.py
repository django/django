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
        raise ValidationError(_(u'Enter a valid e-mail address.'), code='invalid')

slug_re = re.compile(r'^[-\w]+$')

def validate_slug(value):
    if not slug_re.search(smart_unicode(value)):
        raise ValidationError(
            _(u"Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."),
            code='invalid'
        )

ipv4_re = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$')

def validate_ipv4_address(value):
    if not ipv4_re.search(smart_unicode(value)):
        raise ValidationError(
            _(u'Enter a valid IPv4 address.'),
            code="invalid"
        )


class MaxValueValidator(object):
    def __init__(self, max_value):
        self.max_value = max_value

    def __call__(self, value):
        if value > self.max_value:
            raise ValidationError(
                _(u'Ensure this value is less than or equal to %s.') % self.max_value,
                code='max_value',
                params=(self.max_value,)
            )

class MinValueValidator(object):
    def __init__(self, min_value):
        self.min_value = min_value

    def __call__(self, value):
        if value < self.min_value:
            raise ValidationError(
                _(u'Ensure this value is greater than or equal to %s.') % self.min_value,
                code='min_value',
                params=(self.min_value,)
            )

class MinLengthValidator(object):
    def __init__(self, min_length):
        self.min_length = min_length

    def __call__(self, value):
        value_len = len(value)
        if value_len < self.min_length:
            raise ValidationError(
                _(u'Ensure this value has at least %(min)d characters (it has %(length)d).'),
                code='min_length',
                params={ 'min': self.min_length, 'length': value_len}
            )

class MaxLengthValidator(object):
    def __init__(self, max_length):
        self.max_length = max_length

    def __call__(self, value):
        value_len = len(value)
        if value_len > self.max_length:
            raise ValidationError(
                _(u'Ensure this value has at most %(max)d characters (it has %(length)d).'),
                code='max_length',
                params={ 'max': self.max_length, 'length': value_len}
            )

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
