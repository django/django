import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

def validate_integer(value, all_values={}, model_instance=None):
    try:
        int(value)
    except (ValueError, TypeError), e:
        raise ValidationError('')

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9]+(?:-*[A-Z0-9]+)*\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

def validate_email(value, all_values={}, model_instance=None):
    if not email_re.search(smart_unicode(value)):
        raise ValidationError(_(u'Enter a valid e-mail address.'))
