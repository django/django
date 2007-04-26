"""
Iceland specific form helpers.
"""

from django.newforms import ValidationError
from django.newforms.fields import RegexField, EMPTY_VALUES
from django.newforms.widgets import Select
from django.utils.translation import gettext

class ISIdNumberField(RegexField):
    """
    Icelandic identification number (kennitala). This is a number every citizen
    of Iceland has.
    """
    def __init__(self, *args, **kwargs):
        error_msg = gettext(u'Enter a valid Icelandic identification number. The format is XXXXXX-XXXX.')
        kwargs['min_length'],kwargs['max_length'] = 10,11
        super(ISIdNumberField, self).__init__(r'^\d{6}(-| )?\d{4}$', error_message=error_msg, *args, **kwargs)

    def clean(self, value):
        value = super(ISIdNumberField, self).clean(value)

        if value in EMPTY_VALUES:
            return u''

        value = self._canonify(value)
        if self._validate(value):
            return self._format(value)
        else:
            raise ValidationError(gettext(u'The Icelandic identification number is not valid.'))

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
        return sum(int(value[i]) * check[i] for i in range(10)) % 11 == 0

    def _format(self, value):
        """
        Takes in the value in canonical form and returns it in the common
        display format.
        """
        return value[:6]+'-'+value[6:]

class ISPhoneNumberField(RegexField):
    """
    Icelandic phone number. Seven digits with an optional hyphen or space after
    the first three digits.
    """
    def __init__(self, *args, **kwargs):
        kwargs['min_length'], kwargs['max_length'] = 7,8
        super(ISPhoneNumberField, self).__init__(r'^\d{3}(-| )?\d{4}$', *args, **kwargs)

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
        from is_postalcodes import IS_POSTALCODES
        super(ISPostalCodeSelect, self).__init__(attrs, choices=IS_POSTALCODES)

