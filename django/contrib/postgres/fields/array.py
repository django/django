import json

from django.contrib.postgres import lookups
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.validators import ArrayMaxLengthValidator
from django.core import checks, exceptions
from django.db.models import Field, IntegerField, Transform
from django.db.models.lookups import Exact
from django.utils import six
from django.utils.translation import string_concat, ugettext_lazy as _

from .utils import AttributeSetter

__all__ = ['ArrayField']


class ArrayField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'item_invalid': _('Item %(nth)s in the array did not validate: '),
        'nested_array_mismatch': _('Nested arrays must have the same length.'),
    }

    def __init__(self, base_field, size=None, **kwargs):
        self.base_field = base_field
        self.size = size
        if self.size:
            self.default_validators = self.default_validators[:]
            self.default_validators.append(ArrayMaxLengthValidator(self.size))
        super(ArrayField, self).__init__(**kwargs)

    def check(self, **kwargs):
        errors = super(ArrayField, self).check(**kwargs)
        if self.base_field.rel:
            errors.append(
                checks.Error(
                    'Base field for array cannot be a related field.',
                    hint=None,
                    obj=self,
                    id='postgres.E002'
                )
            )
        else:
            # Remove the field name checks as they are not needed here.
            base_errors = self.base_field.check()
            if base_errors:
                messages = '\n    '.join('%s (%s)' % (error.msg, error.id) for error in base_errors)
                errors.append(
                    checks.Error(
                        'Base field for array has errors:\n    %s' % messages,
                        hint=None,
                        obj=self,
                        id='postgres.E001'
                    )
                )
        return errors

    def set_attributes_from_name(self, name):
        super(ArrayField, self).set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    @property
    def description(self):
        return 'Array of %s' % self.base_field.description

    def db_type(self, connection):
        size = self.size or ''
        return '%s[%s]' % (self.base_field.db_type(connection), size)

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, list) or isinstance(value, tuple):
            return [self.base_field.get_db_prep_value(i, connection, prepared) for i in value]
        return value

    def deconstruct(self):
        name, path, args, kwargs = super(ArrayField, self).deconstruct()
        if path == 'django.contrib.postgres.fields.array.ArrayField':
            path = 'django.contrib.postgres.fields.ArrayField'
        kwargs.update({
            'base_field': self.base_field,
            'size': self.size,
        })
        return name, path, args, kwargs

    def to_python(self, value):
        if isinstance(value, six.string_types):
            # Assume we're deserializing
            vals = json.loads(value)
            value = [self.base_field.to_python(val) for val in vals]
        return value

    def value_to_string(self, obj):
        values = []
        vals = self._get_val_from_obj(obj)
        base_field = self.base_field

        for val in vals:
            obj = AttributeSetter(base_field.attname, val)
            values.append(base_field.value_to_string(obj))
        return json.dumps(values)

    def get_transform(self, name):
        transform = super(ArrayField, self).get_transform(name)
        if transform:
            return transform
        try:
            index = int(name)
        except ValueError:
            pass
        else:
            index += 1  # postgres uses 1-indexing
            return IndexTransformFactory(index, self.base_field)
        try:
            start, end = name.split('_')
            start = int(start) + 1
            end = int(end)  # don't add one here because postgres slices are weird
        except ValueError:
            pass
        else:
            return SliceTransformFactory(start, end)

    def validate(self, value, model_instance):
        super(ArrayField, self).validate(value, model_instance)
        for i, part in enumerate(value):
            try:
                self.base_field.validate(part, model_instance)
            except exceptions.ValidationError as e:
                raise exceptions.ValidationError(
                    string_concat(self.error_messages['item_invalid'], e.message),
                    code='item_invalid',
                    params={'nth': i},
                )
        if isinstance(self.base_field, ArrayField):
            if len({len(i) for i in value}) > 1:
                raise exceptions.ValidationError(
                    self.error_messages['nested_array_mismatch'],
                    code='nested_array_mismatch',
                )

    def run_validators(self, value):
        super(ArrayField, self).run_validators(value)
        for i, part in enumerate(value):
            try:
                self.base_field.run_validators(part)
            except exceptions.ValidationError as e:
                raise exceptions.ValidationError(
                    string_concat(self.error_messages['item_invalid'], ' '.join(e.messages)),
                    code='item_invalid',
                    params={'nth': i},
                )

    def formfield(self, **kwargs):
        defaults = {
            'form_class': SimpleArrayField,
            'base_field': self.base_field.formfield(),
            'max_length': self.size,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)


@ArrayField.register_lookup
class ArrayContains(lookups.DataContains):
    def as_sql(self, qn, connection):
        sql, params = super(ArrayContains, self).as_sql(qn, connection)
        sql = '%s::%s' % (sql, self.lhs.output_field.db_type(connection))
        return sql, params


@ArrayField.register_lookup
class ArrayContainedBy(lookups.ContainedBy):
    def as_sql(self, qn, connection):
        sql, params = super(ArrayContainedBy, self).as_sql(qn, connection)
        sql = '%s::%s' % (sql, self.lhs.output_field.db_type(connection))
        return sql, params


@ArrayField.register_lookup
class ArrayExact(Exact):
    def as_sql(self, qn, connection):
        sql, params = super(ArrayExact, self).as_sql(qn, connection)
        sql = '%s::%s' % (sql, self.lhs.output_field.db_type(connection))
        return sql, params


@ArrayField.register_lookup
class ArrayOverlap(lookups.Overlap):
    def as_sql(self, qn, connection):
        sql, params = super(ArrayOverlap, self).as_sql(qn, connection)
        sql = '%s::%s' % (sql, self.lhs.output_field.db_type(connection))
        return sql, params


@ArrayField.register_lookup
class ArrayLenTransform(Transform):
    lookup_name = 'len'
    output_field = IntegerField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return 'array_length(%s, 1)' % lhs, params


class IndexTransform(Transform):

    def __init__(self, index, base_field, *args, **kwargs):
        super(IndexTransform, self).__init__(*args, **kwargs)
        self.index = index
        self.base_field = base_field

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return '%s[%s]' % (lhs, self.index), params

    @property
    def output_field(self):
        return self.base_field


class IndexTransformFactory(object):

    def __init__(self, index, base_field):
        self.index = index
        self.base_field = base_field

    def __call__(self, *args, **kwargs):
        return IndexTransform(self.index, self.base_field, *args, **kwargs)


class SliceTransform(Transform):

    def __init__(self, start, end, *args, **kwargs):
        super(SliceTransform, self).__init__(*args, **kwargs)
        self.start = start
        self.end = end

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return '%s[%s:%s]' % (lhs, self.start, self.end), params


class SliceTransformFactory(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __call__(self, *args, **kwargs):
        return SliceTransform(self.start, self.end, *args, **kwargs)
