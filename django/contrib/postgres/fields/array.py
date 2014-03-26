import json
import re

from django.core import checks
from django.db.models import Field, Lookup, Transform, IntegerField
from django.utils import six
from django.utils.functional import cached_property


__all__ = ['ArrayField']


class ArrayField(Field):
    empty_strings_allowed = False

    def __init__(self, base_field, **kwargs):
        super(ArrayField, self).__init__(**kwargs)
        self.base_field = base_field

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
    def definition(self):
        return 'Array of %s' % self.base_field.definition

    def db_type(self, connection):
        return self.base_field.db_type(connection) + '[]'

    def get_prep_value(self, value):
        if isinstance(value, list):
            return [self.base_field.get_prep_value(i) for i in value]
        return value

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if lookup_type == 'contains':
            return [self.get_prep_value(value)]
        return super(ArrayField, self).get_db_prep_lookup(lookup_type, value,
                connection, prepared=False)

    def deconstruct(self):
        name, path, args, kwargs = super(ArrayField, self).deconstruct()
        path = 'django.contrib.postgres.fields.ArrayField'
        args.insert(0, self.base_field)
        return name, path, args, kwargs

    def to_python(self, value):
        if isinstance(value, six.string_types):
            # Assume we're deserializing
            vals = json.loads(value)
            value = []
            for val in vals:
                value.append(self.base_field.to_python(val))
        return value

    def value_to_string(self, obj):
        values = []
        vals = self._get_val_from_obj(obj)
        base_field = self.base_field

        class FakeObj(object):
            def __init__(self, value):
                setattr(self, base_field.attname, value)

        for val in vals:
            values.append(base_field.value_to_string(FakeObj(val)))
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
            index = index + 1  # postgres uses 1-indexing
            return IndexTransformFactory(index, self.base_field)
        if re.match('\d+_\d+', name):
            start, end = name.split('_')
            start = int(start) + 1
            end = int(end) + 1
            return SliceTransformFactory(start, end)


class ArrayContainsLookup(Lookup):
    lookup_name = 'contains'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s @> %s' % (lhs, rhs), params


ArrayField.register_lookup(ArrayContainsLookup)


class ArrayOverlapLookup(Lookup):
    lookup_name = 'overlap'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s && %s' % (lhs, rhs), params


ArrayField.register_lookup(ArrayOverlapLookup)


class ArrayLenTransform(Transform):
    lookup_name = 'len'

    @cached_property
    def output_type(self):
        return IntegerField()

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return 'array_length(%s, 1)' % lhs, params


ArrayField.register_lookup(ArrayLenTransform)


class IndexTransform(Transform):

    def __init__(self, index, base_field, *args, **kwargs):
        super(IndexTransform, self).__init__(*args, **kwargs)
        self.index = index
        self.base_field = base_field

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return '%s[%s]' % (lhs, self.index), params

    @cached_property
    def output_type(self):
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

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return '%s[%s:%s]' % (lhs, self.start, self.end), params


class SliceTransformFactory(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __call__(self, *args, **kwargs):
        return SliceTransform(self.start, self.end, *args, **kwargs)
