from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _

from django.contrib.localflavor.mk.mk_choices import MK_MUNICIPALITIES
from django.contrib.localflavor.mk.forms import (UMCNField as UMCNFormField,
    MKIdentityCardNumberField as MKIdentityCardNumberFormField)


class MKIdentityCardNumberField(CharField):

    description = _("Macedonian identity card number")

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 8
        super(MKIdentityCardNumberField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class' : MKIdentityCardNumberFormField}
        defaults.update(kwargs)
        return super(MKIdentityCardNumberField, self).formfield(**defaults)


class MKMunicipalityField(CharField):

    description = _("A Macedonian municipality (2 character code)")

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = MK_MUNICIPALITIES
        kwargs['max_length'] = 2
        super(MKMunicipalityField, self).__init__(*args, **kwargs)


class UMCNField(CharField):

    description = _("Unique master citizen number (13 digits)")

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 13
        super(UMCNField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class' : UMCNFormField}
        defaults.update(kwargs)
        return super(UMCNField, self).formfield(**defaults)
