"""
Iceland specific form helpers.
"""

from __future__ import absolute_import

from django.contrib.localflavor.is_.is_postalcodes import IS_POSTALCODES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import RegexField
from django.forms.widgets import Select
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _


class ISIdNumberField(RegexField):
    """
    Icelandic identification number (kennitala). This is a number every citizen
    of Iceland has.
    """
    default_error_messages = {
        'invalid': _('Enter a valid Icelandic identification number. The format is XXXXXX-XXXX.'),
        'checksum': _(u'The Icelandic identification number is not valid.'),
    }

    def __init__(self, max_length=11, min_length=10, *args, **kwargs):
        super(ISIdNumberField, self).__init__(r'^\d{6}(-| )?\d{4}$',
            max_length, min_length, *args, **kwargs)

    def clean(self, value):
        value = super(ISIdNumberField, self).clean(value)

        if value in EMPTY_VALUES:
            return u''

        value = self._canonify(value)
        if self._validate(value):
            return self._format(value)
        else:
            raise ValidationError(self.error_messages['checksum'])

    def _canonify(self, value):
        """
        Returns the value as only digits.
        """
        return value.replace('-', '').replace(' ', '')

    def _validate(self, value):
        """
        Takes in the value in canonical form and checks the verifier digit. The
        method is modulo 11.
        """
        check = [3, 2, 7, 6, 5, 4, 3, 2, 1, 0]
        return sum([int(value[i]) * check[i] for i in range(10)]) % 11 == 0

    def _format(self, value):
        """
        Takes in the value in canonical form and returns it in the common
        display format.
        """
        return smart_unicode(value[:6]+'-'+value[6:])

class ISPhoneNumberField(RegexField):
    """
    Icelandic phone number. Seven digits with an optional hyphen or space after
    the first three digits.
    """
    def __init__(self, max_length=8, min_length=7, *args, **kwargs):
        super(ISPhoneNumberField, self).__init__(r'^\d{3}(-| )?\d{4}$',
            max_length, min_length, *args, **kwargs)

    def clean(self, value):
        value = super(ISPhoneNumberField, self).clean(value)

        if value in EMPTY_VALUES:
            return u''

        return value.replace('-', '').replace(' ', '')

class ISPostalCodeSelect(Select):
    """
    A Select widget that uses a list of Icelandic postal codes as its choices.
    """
    def __init__(self, attrs=None):
        super(ISPostalCodeSelect, self).__init__(attrs, choices=IS_POSTALCODES)

