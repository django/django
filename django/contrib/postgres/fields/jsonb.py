import json

from psycopg2.extras import Json

from django.contrib.postgres import forms, lookups
from django.core import exceptions
from django.db.models import (
    Field, TextField, Transform, lookups as builtin_lookups,
)
from django.utils.translation import ugettext_lazy as _

__all__ = ['JSONField']


class JsonAdapter(Json):
    """
    Customized psycopg2.extras.Json to allow for a custom encoder.
    """
    def __init__(self, adapted, dumps=None, encoder=None):
        self.encoder = encoder
        super(JsonAdapter, self).__init__(adapted, dumps=dumps)

    def dumps(self, obj):
        options = {'cls': self.encoder} if self.encoder else {}
        return json.dumps(obj, **options)


class JSONField(Field):
    empty_strings_allowed = False
    description = _('A JSON object')
    default_error_messages = {
        'invalid': _("Value must be valid JSON."),
    }

    def __init__(self, verbose_name=None, name=None, encoder=None, **kwargs):
        if encoder and not callable(encoder):
            raise ValueError("The encoder parameter must be a callable object.")
        self.encoder = encoder
        super(JSONField, self).__init__(verbose_name, name, **kwargs)

    def db_type(self, connection):
        return 'jsonb'

    def deconstruct(self):
        name, path, args, kwargs = super(JSONField, self).deconstruct()
        if self.encoder is not None:
            kwargs['encoder'] = self.encoder
        return name, path, args, kwargs

    def get_transform(self, name):
        transform = super(JSONField, self).get_transform(name)
        if transform:
            return transform
        return KeyTransformFactory(name)

    def get_prep_value(self, value):
        if value is not None:
            return JsonAdapter(value, encoder=self.encoder)
        return value

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        options = {'cls': self.encoder} if self.encoder else {}
        try:
            json.dumps(value, **options)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def value_to_string(self, obj):
        return self.value_from_object(obj)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.JSONField}
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)


class KeyTransform(Transform):
    operator = '->'
    nested_operator = '#>'

    def __init__(self, key_name, *args, **kwargs):
        super(KeyTransform, self).__init__(*args, **kwargs)
        self.key_name = key_name

    def as_sql(self, compiler, connection):
        key_transforms = [self.key_name]
        previous = self.lhs
        while isinstance(previous, KeyTransform):
            key_transforms.insert(0, previous.key_name)
            previous = previous.lhs
        lhs, params = compiler.compile(previous)
        if len(key_transforms) > 1:
            return "(%s %s %%s)" % (lhs, self.nested_operator), [key_transforms] + params
        try:
            int(self.key_name)
        except ValueError:
            lookup = "'%s'" % self.key_name
        else:
            lookup = "%s" % self.key_name
        return "(%s %s %s)" % (lhs, self.operator, lookup), params


class KeyTextTransform(KeyTransform):
    operator = '->>'
    nested_operator = '#>>'
    _output_field = TextField()


class KeyTransformTextLookupMixin:
    """
    Mixin for combining with a lookup expecting a text lhs from a JSONField
    key lookup. Make use of the ->> operator instead of casting key values to
    text and performing the lookup on the resulting representation.
    """
    def __init__(self, key_transform, *args, **kwargs):
        assert isinstance(key_transform, KeyTransform)
        key_text_transform = KeyTextTransform(
            key_transform.key_name, *key_transform.source_expressions, **key_transform.extra
        )
        super(KeyTransformTextLookupMixin, self).__init__(key_text_transform, *args, **kwargs)


class KeyTransformIExact(KeyTransformTextLookupMixin, builtin_lookups.IExact):
    pass


class KeyTransformIContains(KeyTransformTextLookupMixin, builtin_lookups.IContains):
    pass


class KeyTransformStartsWith(KeyTransformTextLookupMixin, builtin_lookups.StartsWith):
    pass


class KeyTransformIStartsWith(KeyTransformTextLookupMixin, builtin_lookups.IStartsWith):
    pass


class KeyTransformEndsWith(KeyTransformTextLookupMixin, builtin_lookups.EndsWith):
    pass


class KeyTransformIEndsWith(KeyTransformTextLookupMixin, builtin_lookups.IEndsWith):
    pass


class KeyTransformRegex(KeyTransformTextLookupMixin, builtin_lookups.Regex):
    pass


class KeyTransformIRegex(KeyTransformTextLookupMixin, builtin_lookups.IRegex):
    pass


KeyTransform.register_lookup(KeyTransformIExact)
KeyTransform.register_lookup(KeyTransformIContains)
KeyTransform.register_lookup(KeyTransformStartsWith)
KeyTransform.register_lookup(KeyTransformIStartsWith)
KeyTransform.register_lookup(KeyTransformEndsWith)
KeyTransform.register_lookup(KeyTransformIEndsWith)
KeyTransform.register_lookup(KeyTransformRegex)
KeyTransform.register_lookup(KeyTransformIRegex)


class KeyTransformFactory:

    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)
