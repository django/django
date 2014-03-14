import json

from django.contrib.postgres import forms
from django.contrib.postgres.fields.array import ArrayField
from django.core import exceptions
from django.db.models import Field, Lookup, Transform, TextField
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

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if lookup_type == 'contains':
            return [self.get_prep_value(value)]
        return super(HStoreField, self).get_db_prep_lookup(lookup_type, value,
                connection, prepared=False)

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


@HStoreField.register_lookup
class HStoreContainsLookup(Lookup):
    lookup_name = 'contains'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s @> %s' % (lhs, rhs), params


@HStoreField.register_lookup
class HStoreContainedByLookup(Lookup):
    lookup_name = 'contained_by'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s <@ %s' % (lhs, rhs), params


@HStoreField.register_lookup
class HasKeyLookup(Lookup):
    lookup_name = 'has_key'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s ? %s' % (lhs, rhs), params


@HStoreField.register_lookup
class HasKeysLookup(Lookup):
    lookup_name = 'has_keys'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s ?& %s' % (lhs, rhs), params


class KeyTransform(Transform):
    output_field = TextField()

    def __init__(self, key_name, *args, **kwargs):
        super(KeyTransform, self).__init__(*args, **kwargs)
        self.key_name = key_name

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return "%s -> '%s'" % (lhs, self.key_name), params


class KeyTransformFactory(object):

    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)


@HStoreField.register_lookup
class KeysTransform(Transform):
    lookup_name = 'keys'
    output_field = ArrayField(TextField())

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return 'akeys(%s)' % lhs, params


@HStoreField.register_lookup
class ValuesTransform(Transform):
    lookup_name = 'values'
    output_field = ArrayField(TextField())

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return 'avals(%s)' % lhs, params
