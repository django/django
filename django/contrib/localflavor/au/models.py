from django.utils.translation import ugettext_lazy as _
from django.db.models.fields import CharField

from django.contrib.localflavor.au.au_states import STATE_CHOICES
from django.contrib.localflavor.au import forms

class AUStateField(CharField):

    description = _("Australian State")

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = STATE_CHOICES
        kwargs['max_length'] = 3
        super(AUStateField, self).__init__(*args, **kwargs)


class AUPostCodeField(CharField):

    description = _("Australian Postcode")

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 4
        super(AUPostCodeField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.AUPostCodeField}
        defaults.update(kwargs)
        return super(AUPostCodeField, self).formfield(**defaults)


class AUPhoneNumberField(CharField):

    description = _("Australian Phone number")

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 20
        super(AUPhoneNumberField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.AUPhoneNumberField}
        defaults.update(kwargs)
        return super(AUPhoneNumberField, self).formfield(**defaults)

