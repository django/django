from django.db.models.fields import Field

class USStateField(Field):
    def get_internal_type(self):
        return "USStateField"

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.oracle':
            return 'CHAR(2)'
        else:
            return 'varchar(2)'

    def formfield(self, **kwargs):
        from django.contrib.localflavor.us.forms import USStateSelect
        defaults = {'widget': USStateSelect}
        defaults.update(kwargs)
        return super(USStateField, self).formfield(**defaults)

class PhoneNumberField(Field):
    def get_internal_type(self):
        return "PhoneNumberField"

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.oracle':
            return 'VARCHAR2(20)'
        else:
            return 'varchar(20)'

    def formfield(self, **kwargs):
        from django.contrib.localflavor.us.forms import USPhoneNumberField
        defaults = {'form_class': USPhoneNumberField}
        defaults.update(kwargs)
        return super(PhoneNumberField, self).formfield(**defaults)
