import json

from django.contrib.postgres import forms, lookups
from django.contrib.postgres.fields.array import ArrayField
from django.core import exceptions
from django.db.models import Field, TextField, Transform
from django.utils import six
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

__all__ = ['HStoreField']


class HStoreField(Field):
    empty_strings_allowed = False
    description = _('Map of strings to strings/nulls')
    default_error_messages = {
        'not_a_string': _('The value of "%(key)s" is not a string or null.'),
    }

    def db_type(self, connection):
        return 'hstore'

    def get_transform(self, name):
        transform = super(HStoreField, self).get_transform(name)
        if transform:
            return transform
        return KeyTransformFactory(name)

    def validate(self, value, model_instance):
        super(HStoreField, self).validate(value, model_instance)
        for key, val in value.items():
            if not isinstance(val, six.string_types) and val is not None:
                raise exceptions.ValidationError(
                    self.error_messages['not_a_string'],
                    code='not_a_string',
                    params={'key': key},
                )

    def to_python(self, value):
        if isinstance(value, six.string_types):
            value = json.loads(value)
        return value

    def value_to_string(self, obj):
        return json.dumps(self.value_from_object(obj))

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.HStoreField,
        }
        defaults.update(kwargs)
        return super(HStoreField, self).formfield(**defaults)

    def get_prep_value(self, value):
        value = super(HStoreField, self).get_prep_value(value)

        if isinstance(value, dict):
            prep_value = {}
            for key, val in value.items():
                key = force_text(key)
                if val is not None:
                    val = force_text(val)
                prep_value[key] = val
            value = prep_value

        if isinstance(value, list):
            value = [force_text(item) for item in value]

        return value


HStoreField.register_lookup(lookups.DataContains)
HStoreField.register_lookup(lookups.ContainedBy)
HStoreField.register_lookup(lookups.HasKey)
HStoreField.register_lookup(lookups.HasKeys)
HStoreField.register_lookup(lookups.HasAnyKeys)


class KeyTransform(Transform):
    output_field = TextField()

    def __init__(self, key_name, *args, **kwargs):
        super(KeyTransform, self).__init__(*args, **kwargs)
        self.key_name = key_name

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "(%s -> '%s')" % (lhs, self.key_name), params


class KeyTransformFactory(object):

    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)


@HStoreField.register_lookup
class KeysTransform(Transform):
    lookup_name = 'keys'
    function = 'akeys'
    output_field = ArrayField(TextField())


@HStoreField.register_lookup
class ValuesTransform(Transform):
    lookup_name = 'values'
    function = 'avals'
    output_field = ArrayField(TextField())
