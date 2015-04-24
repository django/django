import copy
import re
import weakref
from collections import OrderedDict
from itertools import chain

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields import Field
from django.db.models.fields.composite_lookups import (
    CompositeExact, CompositeIn, CompositeIsNull, SubfieldTransform,
)
from django.utils import six
from django.utils.functional import cached_property
from django.utils.observables import Observable, ObservableDict

__all__ = ('constrain', 'CompositeField')


def constrain(*fields, **kwargs):
    """
    Add a database constraint which applies to the given fields, and adds a
    descriptor to the model which returns the values of fields as a dict.

    Currently supported kwargs are:
        - unique: Applies a UNIQUE constraint to the model's table, ensuring
          that any combination of the fields values on the database table
          is unique. Default is `False`
        - db_index: Adds an index to the model's table, which indexes

    If 'fields' is empty, a composite field will still be created on the model,
    but it will have no data.
    If 'fields' contains a single element, then the constraints are still
    applied to the field, even if that field is not unique or indexed.

    eg.

    class Model(Model):
        x = IntegerField(unique=False)
        x_unique = models.constrain(x, unique=True)

    The presence of x_unique will still add a unique constraint on x to the
    table, even though the field has unique=False.


    It is possible to constrain fields specified on a base class, by passing
    in the field as a string.

    eg.

    class Base(Model):
        x = IntegerField(unique=False)

    class Concrete(Base):
        y = IntegerField()
        _ = models.constrain('x', y, unique=True)

    The previous example also demonstrates how to add an unnamed constraint
    to a model. CompositeFields whose name consist solely of a string of
    underscore characters will not contribute an accessor to the containing
    class, nor will they be available via the query API.
    """
    unique = kwargs.pop('unique', False)
    db_index = kwargs.pop('db_index', True)
    composite_field = CompositeField(unique=unique, db_index=db_index)

    # Loads subfields. This isn't called until the app registry is ready,
    # so all fields are guaranteed to exist on the model.
    def lazy_subfields(model_cls):
        subfields = OrderedDict()
        for field in fields:
            # If the field is defined on a supertype, there is no field
            # available in the current scope to pass the field into `constrain`
            # (and SuperType.field_name doesn't work because metaclasses).
            #
            # Thus constrained fields can be passed in by their name on the
            # model.
            if isinstance(field, six.string_types):
                field = model_cls._meta.get_field(field)
                subfields[field.name] = Subfield(
                    composite_field, field, managed=False
                )
                continue
            # The field may be copied from a parent model during inheritance
            # The subfield should use the copied model
            for model_field in model_cls._meta.fields:
                if field == model_field:
                    assert hasattr(field, 'model'), 'Not all modules loaded'
                    subfields[field.name] = Subfield(
                        composite_field, model_field, managed=False
                    )
                    break
            else:
                # The field was declared inside the parameter list of
                # constrain
                # eg. models.constrain(IntegerField(), ...)
                #
                # It can also happen if the field is declared outside
                # the class definition
                raise FieldDoesNotExist(
                    'Field cannot be declared inside call to `constrain`'
                )
        return subfields
    composite_field._lazy_subfields = lazy_subfields

    return composite_field


class CompositeFieldBase(type):
    # The composite field metaclass isn't required until DEP 192, but it doesn't
    # do any harm to add it now.

    def __new__(cls, name, bases, attrs):
        return super(CompositeFieldBase, cls).__new__(cls, name, bases, attrs)


class CompositeField(six.with_metaclass(CompositeFieldBase, Field)):
    is_composite = True
    concrete = False

    _UNNAMED_FIELD_REGEX = re.compile('_+$')

    def __init__(self, **kwargs):
        super(CompositeField, self).__init__(**kwargs)

    @cached_property
    def subfields(self):
        if not hasattr(self, 'model'):
            raise AttributeError(
                'CompositeField does not have `subfields` until '
                'contribute_to_class has been called'
            )
        # We don't actually need the entire app registry to load, but  we do
        # need all the other fields on the model to be fully finalized, in order
        # for it to be possible to populate the subfields with the correct
        # model names. Waiting for the app registry to be loaded might be late,
        # but at least we can be confident that everything has loaded by then
        self.model._meta.apps.get_models()

        if hasattr(self, '_lazy_subfields'):
            return self._lazy_subfields(self.model)
        else:
            # DEP 192
            raise NotImplementedError('standalone fields')

    @cached_property
    def is_unnamed(self):
        return bool(self._UNNAMED_FIELD_REGEX.match(self.name))

    def contribute_to_class(self, model_cls, name, virtual_only=False):
        super(CompositeField, self).contribute_to_class(
            model_cls, name, virtual_only=True
        )
        if not self.is_unnamed:
            setattr(model_cls, name, CompositeFieldDescriptor(self))

    def get_subfield(self, subfield_name):
        if subfield_name in self.subfields:
            return self.subfields[subfield_name]
        raise FieldDoesNotExist(subfield_name)

    def get_lookup(self, lookup_name):
        if self.is_unnamed:
            raise LookupError(
                'Cannot perform lookup on unnamed composite field'
            )
        if lookup_name == 'exact':
            return CompositeExact
        elif lookup_name == 'isnull':
            return CompositeIsNull
        elif lookup_name == 'in':
            return CompositeIn

    def get_transform(self, lookup_name):
        if lookup_name in self.subfields:
            return SubfieldTransform

    def value_to_dict(self, value):
        """
        Takes an arbitrary python object and returns a mapping of subfield
        names to values. If the `CompositeField` is nullable and the value
        is null, this method is expected to still return a python dict.

        By default, just returns value unchanged. The method should be overriden
        by CompositeField subclasses
        """
        return value

    def value_from_dict(self, field_dict):
        """
        Takes a mapping of subfield names to their current model values and
        returns a custom object instance. The argument will never be `None`.

        The returned value must be one of:
            - None
            - A tuple of field values
            - ObservableDict/ObservableOrderedDict
            - A python object which mixes in Observable

        The values of the composite field's subfields are bound to the values
        returned by this method to the returned value, so any change record
        emitted by the observable will update the subfield with the same name
        as the record's key.

        By default, just wraps the field dict in an ObservableDict. This method
        should be overriden by CompositeField subclasses
        """
        return ObservableDict(field_dict)

    def check(self, **kwargs):
        return chain(
            super(CompositeField, self).check(**kwargs),
            self._check_subfields
        )

    def _check_subfields(self, **kwargs):
        for subfield in self.subfields.values:
            # TODO: Field error codes
            if subfield.is_relation:
                yield checks.Error(
                    'Subfield %s cannot be a relation field' % subfield.name,
                    hint=None,
                    obj=self,
                    id='fields.E401'
                )
            if subfield.is_composite:
                yield checks.Error(
                    'Subfield %s cannot be a composite field' % subfield.name,
                    hint=None,
                    obj=self,
                    id='fields.E402'
                )
        subfield_messages = chain.from_iterable(
            field.check(**kwargs) for field in self.subfields.values
        )
        for msg in chain.from_iterable(subfield_messages):
            yield msg

    def _check_field_name(self):
        for err in super(CompositeField, self)._check_field_name():
            if err.id in ('fields.E001', 'fields.E002') and self.is_unnamed:
                continue
            yield err

    def __deepcopy__(self, memodict):
        obj = super(CompositeField, self).__deepcopy__(memodict)
        if hasattr(self, '_subfields'):
            # DEP 192
            raise NotImplementedError('Standalone composite field')
        elif hasattr(self, '_lazy_subfields'):
            obj._lazy_subfields = self._lazy_subfields
        return obj

    def get_attname_column(self):
        return self.get_attname(), None

    def get_col(self, alias, output_field=None):
        assert (output_field is None or output_field is self)
        from django.db.models.fields.composite_lookups import CompositeCol
        return CompositeCol(alias, self)

    def from_db_value(self, value, expression, connection, context):
        return self.value_from_dict(dict(zip(self.subfields, value)))


class Subfield(Field):
    """
    A Subfield is a field which stores the value of another field. The subfield
    is an implementation detail of the composite field API and may be removed
    without warning.

    Subfields can either be managed or unmanaged. An unmanaged subfield exists
    independently of the composite field, on the model's definition, a
    managed subfield is created as part of a standalone composite field
    definition and is contributed to the model by the composite field
    """
    _OWN_ATTRS = ('composite_field', 'delegate_field', 'managed')

    def __init__(self, composite_field, delegate_field, managed=False):
        self.composite_field = composite_field
        self.delegate_field = delegate_field
        self.managed = managed

    @cached_property
    def attname(self):
        if not self.managed:
            return self.delegate_field.attname
        return '%s__%s' % (self.composite_field.name, self.delegate_field.name)

    @property
    def creation_counter(self):
        return self.composite_field.creation_counter

    @property
    def subfield_creation_counter(self):
        return self.delegate_field.creation_counter

    def check(self, **kwargs):
        if not self.managed:
            return self.delegate_field.check(**kwargs)
        # An unmanaged subfield is already checked by the model
        return []

    # TODO: A subfield cannot have any of the names 'exact', 'isnull', 'in'

    def __getattr__(self, attr):
        if attr in Subfield._OWN_ATTRS:
            return self.__dict__[attr]
        return getattr(self.delegate_field, attr)

    def __setattr__(self, attr, value):
        if attr in Subfield._OWN_ATTRS:
            self.__dict__[attr] = value
        else:
            setattr(self.delegate_field, attr, value)

    def __deepcopy__(self, memodict):
        obj = copy.copy(self)
        obj.composite_field = memodict[id(self.composite_field)]
        obj.delegate_field = copy.deepcopy(self.delegate_field)
        return obj


class CompositeFieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner):
        if instance is None:
            return self
        subfield_dict = dict()
        for subfield_name, subfield in self.field.subfields.items():
            value = getattr(instance, subfield.attname)
            subfield_dict[subfield_name] = value
        result = self.field.value_from_dict(subfield_dict)

        if isinstance(result, Observable):
            self.bind_observer(instance, result)
            return result
        elif result is None or isinstance(result, tuple):
            return result
        else:
            # We should just return here, rather than raising an error.
            # A functionally-minded developer might prefer immutable composite
            # field instances, in which case Observable is not required
            # Useful sanity check for the moment.
            raise AttributeError(
                'CompositeField.value_from_dict must return an observable '
                'instance')

    def __set__(self, instance, value):
        # Update all subfield values immediately
        subfield_dict = self.field.value_to_dict(value)
        for subfield_name, subfield_value in subfield_dict.items():
            subfield = self.field.get_subfield(subfield_name)
            setattr(instance, subfield.attname, subfield_value)
        if isinstance(value, Observable):
            value = self.field.value_from_dict(
                self.field.value_to_dict(value)
            )
            self.bind_observer(instance, value)

    def bind_observer(self, instance, observable):
        """
        Adds an observer of the observable subfield value to the given instance
        The observers of an observable are stored as weak references, so attach
        a reference to the observer to the ModelState.

        This causes the observer to get gc'd when the model instance is gc'd,
        and the observer to try to update a non-existent model instance.
        """
        observers = instance._state.field_observers.setdefault(self.field, [])

        observer = SubfieldObserver(self.field, instance)
        observable.add_observer(observer)
        observers.append(observer)


class SubfieldObserver(object):
    def __init__(self, composite_field, model_instance):
        self.field = composite_field
        # Avoid a circular reference to the model instance which would prevent
        # a gc.
        self.instance_ref = weakref.ref(model_instance)

    def handle_changes(self, change_records):
        instance = self.instance_ref()
        if instance is None:
            return
        for record in change_records:
            try:
                subfield = self.field.get_subfield(record.key)
            except FieldDoesNotExist:
                continue

            # FIXME: We only have one-way binding, so a subfield value is
            # allowed to be updated without affecting the state of the model
            # instance. As a sanity check until this gets ready for production,
            # ensure that the value remains in sync
            assert getattr(instance, subfield.attname) == record.old, (
                'Subfield value is not synchronized'
            )

            setattr(instance, subfield.attname, record.new)
