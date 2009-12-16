from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models.fields import Field, CharField
from django.contrib.localflavor.us.us_states import STATE_CHOICES

class USStateField(CharField):

    description = _("U.S. state (two uppercase letters)")

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = STATE_CHOICES
        kwargs['max_length'] = 2
        super(USStateField, self).__init__(*args, **kwargs)

class PhoneNumberField(Field):

    description = _("Phone number")

    def get_internal_type(self):
        return "PhoneNumberField"

    def db_type(self):
        if settings.DATABASE_ENGINE == 'oracle':
            return 'VARCHAR2(20)'
        else:
            return 'varchar(20)'

    def formfield(self, **kwargs):
        from django.contrib.localflavor.us.forms import USPhoneNumberField
        defaults = {'form_class': USPhoneNumberField}
        defaults.update(kwargs)
        return super(PhoneNumberField, self).formfield(**defaults)

