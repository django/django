import json

from django.contrib.postgres import forms, lookups
from django.contrib.postgres.fields.array import ArrayField
from django.core import exceptions
from django.db.models import Field, TextField, Transform
from django.utils import six
from django.utils.translation import ugettext_lazy as _

__all__ = ['HStoreField']


class HStoreField(Field):
    empty_strings_allowed = False
    description = _('Map of strings to strings')
    default_error_messages = {
        'not_a_string': _('The value of "%(key)s" is not a string.'),
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
            if not isinstance(val, six.string_types):
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
        value = self._get_val_from_obj(obj)
        return json.dumps(value)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.HStoreField,
        }
        defaults.update(kwargs)
        return super(HStoreField, self).formfield(**defaults)


HStoreField.register_lookup(lookups.DataContains)
HStoreField.register_lookup(lookups.ContainedBy)


@HStoreField.register_lookup
class HasKeyLookup(lookups.PostgresSimpleLookup):
    lookup_name = 'has_key'
    operator = '?'


@HStoreField.register_lookup
class HasKeysLookup(lookups.PostgresSimpleLookup):
    lookup_name = 'has_keys'
    operator = '?&'


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
class KeysTransform(lookups.FunctionTransform):
    lookup_name = 'keys'
    function = 'akeys'
    output_field = ArrayField(TextField())


@HStoreField.register_lookup
class ValuesTransform(lookups.FunctionTransform):
    lookup_name = 'values'
    function = 'avals'
    output_field = ArrayField(TextField())
