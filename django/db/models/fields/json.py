import json

from django import forms
from django.core import exceptions
from django.db.models import lookups
from django.db.models.lookups import (
    FieldGetDbPrepValueMixin, Lookup, Transform,
)
from django.db.utils import NotSupportedError
from django.utils.translation import gettext_lazy as _

from . import Field
from .mixins import CheckFieldDefaultMixin


class JSONField(CheckFieldDefaultMixin, Field):
    description = _('A JSON object')
    default_error_messages = {
        'invalid': _('Value must be valid JSON.'),
    }
    _default_hint = ('dict', '{}')

    def __init__(
        self, verbose_name=None, name=None, encoder=None,
        decoder=None, *args, **kwargs
    ):
        self.encoder, self.decoder = encoder, decoder
        super().__init__(verbose_name, name, *args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        path = 'django.db.models.JSONField'
        if self.encoder is not None:
            kwargs['encoder'] = self.encoder
        if self.decoder is not None:
            kwargs['decoder'] = self.decoder
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        elif connection.vendor == 'postgresql' and self.decoder is None:
            return value
        else:
            try:
                return json.loads(value, cls=self.decoder)
            except json.JSONDecodeError:
                return value

    def get_internal_type(self):
        return 'JSONField'

    def get_prep_value(self, value):
        if value is None:
            return value
        return json.dumps(value, cls=self.encoder)

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        return KeyTransformFactory(name)

    def select_format(self, compiler, sql, params):
        if compiler.connection.vendor == 'postgresql' and self.decoder is not None:
            # Avoid psycopg2's automatic decoding to allow custom decoder
            return '%s::text' % sql, params
        return super().select_format(compiler, sql, params)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        try:
            json.dumps(value, cls=self.encoder)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def value_to_string(self, obj):
        return self.value_from_object(obj)

    def formfield(self, **kwargs):
        return super().formfield(**{
            'form_class': forms.JSONField,
            'encoder': self.encoder,
            'decoder': self.decoder,
            **kwargs,
        })


def compile_json_path(key_transforms):
    path = ['$']
    for key_transform in key_transforms:
        try:
            num = int(key_transform)
        except ValueError:  # non-integer
            path.append('.')
            path.append(json.dumps(key_transform))
        else:
            path.append('[%s]' % num)
    return ''.join(path)


class SimpleFunctionOperatorMixin(FieldGetDbPrepValueMixin):
    def as_sql_function(self, compiler, connection, template, flipped=False):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        if flipped:
            return template % (rhs, lhs), tuple(rhs_params) + tuple(lhs_params)
        else:
            return template % (lhs, rhs), tuple(lhs_params) + tuple(rhs_params)

    def as_sql_operator(self, compiler, connection, operator):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = tuple(lhs_params) + tuple(rhs_params)
        return '%s %s %s' % (lhs, operator, rhs), params

    def as_postgresql(self, compiler, connection):
        return self.as_sql_operator(compiler, connection, self.postgres_operator)

    def as_sql(self, compiler, connection):
        raise NotSupportedError(
            '%s lookup is not supported by this database backend.' % self.lookup_name
        )


class HasKeyLookup(SimpleFunctionOperatorMixin, Lookup):
    logical_operator = None

    def as_sql(self, compiler, connection, template=None):
        if isinstance(self.lhs, KeyTransform):
            lhs, lhs_params, lhs_key_transforms = self.lhs.preprocess_lhs(compiler, connection)
        else:
            lhs, lhs_params, lhs_key_transforms = *compiler.compile(self.lhs), []
        rhs = [self.rhs] if not isinstance(self.rhs, (list, tuple)) else list(self.rhs)
        rhs_params = []
        for key in rhs:
            if isinstance(key, str):
                rhs_params.insert(0, compile_json_path(lhs_key_transforms + [key]))
            else:
                if isinstance(key, KeyTransform):
                    _, _, key_transforms = key.preprocess_lhs(compiler, connection)
                else:
                    key_transforms = []
                rhs_params.insert(0, compile_json_path(lhs_key_transforms + key_transforms))
        sql = template % lhs
        if self.logical_operator:
            # Add condition for each key.
            sql = '(%s)' % self.logical_operator.join([sql] * len(rhs_params))
        return sql, tuple(lhs_params) + tuple(rhs_params)

    def as_mysql(self, compiler, connection):
        return self.as_sql(compiler, connection, template="JSON_CONTAINS_PATH(%s, 'one', %%s)")

    def as_oracle(self, compiler, connection):
        sql, params = self.as_sql(compiler, connection, template="JSON_EXISTS(%s, '%%s')")
        # Add paths directly into SQL because path expressions cannot be passed
        # as bind variables on Oracle.
        return sql % tuple(params), []

    def as_sqlite(self, compiler, connection):
        return self.as_sql(compiler, connection, template='JSON_TYPE(%s, %%s) IS NOT NULL')


@JSONField.register_lookup
class HasKey(HasKeyLookup):
    lookup_name = 'has_key'
    postgres_operator = '?'
    prepare_rhs = False


@JSONField.register_lookup
class HasAnyKeys(HasKeyLookup):
    lookup_name = 'has_any_keys'
    postgres_operator = '?|'
    logical_operator = ' OR '

    def get_prep_lookup(self):
        return [
            str(item) if not isinstance(item, KeyTransform) else item
            for item in self.rhs
        ]


@JSONField.register_lookup
class HasKeys(HasAnyKeys):
    lookup_name = 'has_keys'
    postgres_operator = '?&'
    logical_operator = ' AND '


@JSONField.register_lookup
class DataContains(SimpleFunctionOperatorMixin, Lookup):
    lookup_name = 'contains'
    postgres_operator = '@>'

    def as_mysql(self, compiler, connection, flipped=False):
        return super().as_sql_function(
            compiler, connection, template="JSON_CONTAINS(%s, %s, '$')", flipped=flipped
        )

    def as_oracle(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        if isinstance(self.rhs, KeyTransform):
            _, _, key_transforms = self.rhs.preprocess_lhs(compiler, connection)
            return "JSON_EXISTS(%s, '%s')" % (lhs, compile_json_path(key_transforms)), []
        else:
            rhs = json.loads(self.rhs)
        if isinstance(rhs, dict):
            if not rhs:
                return "DBMS_LOB.SUBSTR(%s) LIKE '{%%%%}'" % lhs, []
            conditions = []
            for key, value in rhs.items():
                k = json.dumps(key)
                if value is None:
                    conditions.append(
                        "(JSON_EXISTS(%s, '$.%s') AND"
                        " COALESCE(JSON_QUERY(%s, '$.%s'), JSON_VALUE(%s, '$.%s')) IS NULL)" % ((lhs, k) * 3)
                    )
                elif isinstance(value, (list, dict)):
                    conditions.append(
                        "JSON_QUERY(%s, '$.%s') = JSON_QUERY('{\"val\": %s}', '$.val')" % (lhs, k, json.dumps(value))
                    )
                else:
                    conditions.append(
                        "JSON_VALUE(%s, '$.%s') = JSON_VALUE('{\"val\": %s}', '$.val')" % (lhs, k, json.dumps(value))
                    )
            return ' AND '.join(conditions), []
        else:
            return 'DBMS_LOB.SUBSTR(%s) = %%s' % lhs, [self.rhs]

    def as_sqlite(self, compiler, connection, flipped=False):
        return super().as_sql_function(
            compiler, connection, template='django_json_contains(%s, %s)', flipped=flipped
        )


@JSONField.register_lookup
class ContainedBy(DataContains):
    lookup_name = 'contained_by'
    postgres_operator = '<@'

    def as_mysql(self, compiler, connection):
        return super().as_mysql(compiler, connection, flipped=True)

    def as_oracle(self, compiler, connection):
        return super().as_sql(compiler, connection)

    def as_sqlite(self, compiler, connection):
        return super().as_sqlite(compiler, connection, flipped=True)


@JSONField.register_lookup
class JSONExact(lookups.Exact):
    can_use_none_as_rhs = True

    def process_lhs(self, compiler, connection):
        lhs, lhs_params = super().process_lhs(compiler, connection)
        if connection.vendor == 'sqlite':
            rhs, rhs_params = super().process_rhs(compiler, connection)
            if rhs == '%s' and rhs_params == [None]:
                # Need to use JSON_TYPE instead of JSON_EXTRACT
                # to determine JSON null values.
                lhs = "JSON_TYPE(%s, '$')" % lhs
        return lhs, lhs_params

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        # Treat None lookup values as null.
        if rhs == '%s' and rhs_params == [None]:
            rhs, rhs_params = ('%s', ['null'])
        if connection.vendor == 'mysql':
            func = ["JSON_EXTRACT(%s, '$')" for value in rhs_params]
            rhs = rhs % tuple(func)
        return rhs, rhs_params


class KeyTransform(Transform):
    postgres_operator = '->'
    postgres_nested_operator = '#>'

    def __init__(self, key_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_name = key_name

    def preprocess_lhs(self, compiler, connection, lhs_only=False):
        if not lhs_only:
            key_transforms = [self.key_name]
        previous = self.lhs
        while isinstance(previous, KeyTransform):
            if not lhs_only:
                key_transforms.insert(0, previous.key_name)
            previous = previous.lhs
        lhs, params = compiler.compile(previous)
        return (lhs, params, key_transforms) if not lhs_only else (lhs, params)

    def as_mysql(self, compiler, connection):
        lhs, params, key_transforms = self.preprocess_lhs(compiler, connection)
        json_path = compile_json_path(key_transforms)
        return 'JSON_EXTRACT(%s, %%s)' % lhs, tuple(params) + (json_path,)

    def as_oracle(self, compiler, connection):
        lhs, params, key_transforms = self.preprocess_lhs(compiler, connection)
        json_path = compile_json_path(key_transforms)
        return "COALESCE(JSON_QUERY(%s, '%s'), JSON_VALUE(%s, '%s'))" % ((lhs, json_path) * 2), tuple(params)

    def as_postgresql(self, compiler, connection):
        lhs, params, key_transforms = self.preprocess_lhs(compiler, connection)
        if len(key_transforms) > 1:
            return '(%s %s %%s)' % (lhs, self.postgres_nested_operator), params + [key_transforms]
        try:
            lookup = int(self.key_name)
        except ValueError:
            lookup = self.key_name
        return '(%s %s %%s)' % (lhs, self.postgres_operator), tuple(params) + (lookup,)

    def as_sqlite(self, compiler, connection):
        lhs, params, key_transforms = self.preprocess_lhs(compiler, connection)
        json_path = compile_json_path(key_transforms)
        return 'JSON_EXTRACT(%s, %%s)' % lhs, tuple(params) + (json_path,)


class KeyTextTransform(KeyTransform):
    postgres_operator = '->>'
    postgres_nested_operator = '#>>'


class KeyTransformTextLookupMixin:
    """
    Mixin for combining with a lookup expecting a text lhs from a JSONField
    key lookup. On PostgreSQL, make use of the ->> operator instead of casting
    key values to text and performing the lookup on the resulting representation.
    On MySQL, JSON_UNQUOTE is applied to the lhs.
    """
    def __init__(self, key_transform, *args, **kwargs):
        if not isinstance(key_transform, KeyTransform):
            raise TypeError(
                'Transform should be an instance of KeyTransform in order to use this lookup.'
            )
        key_text_transform = KeyTextTransform(
            key_transform.key_name, *key_transform.source_expressions, **key_transform.extra
        )
        super().__init__(key_text_transform, *args, **kwargs)


class KeyTransformNumericLookupMixin:
    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        if connection.vendor != 'postgresql':
            rhs_params = [json.loads(value) for value in rhs_params]
        return rhs, rhs_params


class CaseInsensitiveMixin:
    def process_lhs(self, compiler, connection):
        lhs, lhs_params = super().process_lhs(compiler, connection)
        if connection.vendor == 'mysql':
            return 'LOWER(%s)' % lhs, lhs_params
        return lhs, lhs_params

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        if connection.vendor == 'mysql':
            return 'LOWER(%s)' % rhs, rhs_params
        return rhs, rhs_params


@KeyTransform.register_lookup
class KeyTransformIsNull(lookups.IsNull):
    def as_oracle(self, compiler, connection):
        if isinstance(self.lhs, KeyTransform):
            prev_lhs, prev_params, key_transforms = self.lhs.preprocess_lhs(compiler, connection)
        else:
            prev_lhs, prev_params, key_transforms = *compiler.compile(self.lhs), []
        json_path = compile_json_path(key_transforms)
        if self.rhs:
            return (
                "(NOT JSON_EXISTS(%s, '%s') OR JSON_QUERY(%s, '$') IS NULL)" % (prev_lhs, json_path, prev_lhs),
                prev_params
            )
        else:
            return "JSON_EXISTS(%s, '%s')" % (prev_lhs, json_path), prev_params

    def as_sqlite(self, compiler, connection):
        lhs, lhs_params = super().process_lhs(compiler, connection)
        if isinstance(self.lhs, KeyTransform):
            prev_lhs, prev_params = self.lhs.preprocess_lhs(compiler, connection, lhs_only=True)
        else:
            prev_lhs, prev_params = compiler.compile(self.lhs)
        if self.rhs:
            return 'JSON_TYPE(%s, %%s) IS NULL' % prev_lhs, lhs_params
        else:
            return 'JSON_TYPE(%s, %%s) IS NOT NULL' % prev_lhs, lhs_params


@KeyTransform.register_lookup
class KeyTransformExact(JSONExact):
    def process_lhs(self, compiler, connection):
        lhs, lhs_params = super().process_lhs(compiler, connection)
        if connection.vendor == 'sqlite':
            rhs, rhs_params = super().process_rhs(compiler, connection)
            if rhs == '%s' and rhs_params == ['null']:
                if isinstance(self.lhs, KeyTransform):
                    lhs, params = self.lhs.preprocess_lhs(compiler, connection, lhs_only=True)
                else:
                    lhs, params = compiler.compile(self.lhs)
                lhs = 'JSON_TYPE(%s, %%s)' % lhs
        return lhs, lhs_params

    def process_rhs(self, compiler, connection):
        if isinstance(self.rhs, KeyTransform):
            rhs, rhs_params = super(lookups.Exact, self).process_rhs(compiler, connection)
            if connection.vendor == 'oracle':
                rhs_params *= 2
            return rhs, rhs_params
        else:
            rhs, rhs_params = super().process_rhs(compiler, connection)
        if connection.vendor == 'oracle':
            func = []
            for value in rhs_params:
                val = json.loads(value)
                if isinstance(val, (list, dict)):
                    func.append("JSON_QUERY('{\"val\": %s}', '$.val')" % value)
                else:
                    func.append("JSON_VALUE('{\"val\": %s}', '$.val')" % value)
            rhs = rhs % tuple(func)
            rhs_params = []
        elif connection.vendor == 'sqlite':
            func = ["JSON_EXTRACT(%s, '$')" if value != 'null' else '%s' for value in rhs_params]
            rhs = rhs % tuple(func)
        return rhs, rhs_params

    def as_oracle(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        if rhs_params == ['null']:
            lhs, lhs_params = self.process_lhs(compiler, connection)
            if isinstance(self.lhs, KeyTransform):
                prev_lhs, _, key_transforms = self.lhs.preprocess_lhs(compiler, connection)
            else:
                prev_lhs, _, key_transforms = *compiler.compile(self.lhs), []
            json_path = compile_json_path(key_transforms)
            sql = "(JSON_EXISTS(%s, '%s') AND %s IS NULL)" % (prev_lhs, json_path, lhs)
            return sql, []
        else:
            return super().as_sql(compiler, connection)


@KeyTransform.register_lookup
class KeyTransformIExact(CaseInsensitiveMixin, KeyTransformTextLookupMixin, lookups.IExact):
    pass


@KeyTransform.register_lookup
class KeyTransformIContains(CaseInsensitiveMixin, KeyTransformTextLookupMixin, lookups.IContains):
    pass


@KeyTransform.register_lookup
class KeyTransformContains(KeyTransformTextLookupMixin, lookups.Contains):
    pass


@KeyTransform.register_lookup
class KeyTransformStartsWith(KeyTransformTextLookupMixin, lookups.StartsWith):
    pass


@KeyTransform.register_lookup
class KeyTransformIStartsWith(CaseInsensitiveMixin, KeyTransformTextLookupMixin, lookups.IStartsWith):
    pass


@KeyTransform.register_lookup
class KeyTransformEndsWith(KeyTransformTextLookupMixin, lookups.EndsWith):
    pass


@KeyTransform.register_lookup
class KeyTransformIEndsWith(CaseInsensitiveMixin, KeyTransformTextLookupMixin, lookups.IEndsWith):
    pass


@KeyTransform.register_lookup
class KeyTransformRegex(KeyTransformTextLookupMixin, lookups.Regex):
    pass


@KeyTransform.register_lookup
class KeyTransformIRegex(CaseInsensitiveMixin, KeyTransformTextLookupMixin, lookups.IRegex):
    pass


@KeyTransform.register_lookup
class KeyTransformLte(KeyTransformNumericLookupMixin, lookups.LessThanOrEqual):
    pass


@KeyTransform.register_lookup
class KeyTransformLt(KeyTransformNumericLookupMixin, lookups.LessThan):
    pass


@KeyTransform.register_lookup
class KeyTransformGte(KeyTransformNumericLookupMixin, lookups.GreaterThanOrEqual):
    pass


@KeyTransform.register_lookup
class KeyTransformGt(KeyTransformNumericLookupMixin, lookups.GreaterThan):
    pass


class KeyTransformFactory:

    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)
