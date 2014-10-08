# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import copy
import datetime
import decimal
import math
import warnings
from base64 import b64decode, b64encode
from itertools import tee

from django.apps import apps
from django.db import connection
from django.db.models.lookups import default_lookups, RegisterLookupMixin
from django.db.models.query_utils import QueryWrapper
from django.conf import settings
from django import forms
from django.core import exceptions, validators, checks
from django.utils.datastructures import DictWrapper
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.functional import cached_property, curry, total_ordering, Promise
from django.utils.text import capfirst
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import (smart_text, force_text, force_bytes,
    python_2_unicode_compatible)
from django.utils.ipv6 import clean_ipv6_address
from django.utils import six
from django.utils.itercompat import is_iterable

# Avoid "TypeError: Item in ``from list'' not a string" -- unicode_literals
# makes these strings unicode
__all__ = [str(x) for x in (
    'AutoField', 'BLANK_CHOICE_DASH', 'BigIntegerField', 'BinaryField',
    'BooleanField', 'CharField', 'CommaSeparatedIntegerField', 'DateField',
    'DateTimeField', 'DecimalField', 'EmailField', 'Empty', 'Field',
    'FieldDoesNotExist', 'FilePathField', 'FloatField',
    'GenericIPAddressField', 'IPAddressField', 'IntegerField', 'NOT_PROVIDED',
    'NullBooleanField', 'PositiveIntegerField', 'PositiveSmallIntegerField',
    'SlugField', 'SmallIntegerField', 'TextField', 'TimeField', 'URLField',
)]


class Empty(object):
    pass


class NOT_PROVIDED:
    pass

# The values to use for "blank" in SelectFields. Will be appended to the start
# of most "choices" lists.
BLANK_CHOICE_DASH = [("", "---------")]


def _load_field(app_label, model_name, field_name):
    return apps.get_model(app_label, model_name)._meta.get_field_by_name(field_name)[0]


class FieldDoesNotExist(Exception):
    pass


# A guide to Field parameters:
#
#   * name:      The name of the field specified in the model.
#   * attname:   The attribute to use on the model object. This is the same as
#                "name", except in the case of ForeignKeys, where "_id" is
#                appended.
#   * db_column: The db_column specified in the model (or None).
#   * column:    The database column for this field. This is the same as
#                "attname", except if db_column is specified.
#
# Code that introspects values, or does other dynamic things, should use
# attname. For example, this gets the primary key value of object "obj":
#
#     getattr(obj, opts.pk.attname)

def _empty(of_cls):
    new = Empty()
    new.__class__ = of_cls
    return new


@total_ordering
@python_2_unicode_compatible
class Field(RegisterLookupMixin):
    """Base class for all field types"""

    # Designates whether empty strings fundamentally are allowed at the
    # database level.
    empty_strings_allowed = True
    empty_values = list(validators.EMPTY_VALUES)

    # These track each time a Field instance is created. Used to retain order.
    # The auto_creation_counter is used for fields that Django implicitly
    # creates, creation_counter is used for all user-specified fields.
    creation_counter = 0
    auto_creation_counter = -1
    default_validators = []  # Default set of validators
    default_error_messages = {
        'invalid_choice': _('Value %(value)r is not a valid choice.'),
        'null': _('This field cannot be null.'),
        'blank': _('This field cannot be blank.'),
        'unique': _('%(model_name)s with this %(field_label)s '
                    'already exists.'),
        # Translators: The 'lookup_type' is one of 'date', 'year' or 'month'.
        # Eg: "Title must be unique for pub_date year"
        'unique_for_date': _("%(field_label)s must be unique for "
                             "%(date_field_label)s %(lookup_type)s."),
    }
    class_lookups = default_lookups.copy()

    # Generic field type description, usually overridden by subclasses
    def _description(self):
        return _('Field of type: %(field_type)s') % {
            'field_type': self.__class__.__name__
        }
    description = property(_description)

    def __init__(self, verbose_name=None, name=None, primary_key=False,
            max_length=None, unique=False, blank=False, null=False,
            db_index=False, rel=None, default=NOT_PROVIDED, editable=True,
            serialize=True, unique_for_date=None, unique_for_month=None,
            unique_for_year=None, choices=None, help_text='', db_column=None,
            db_tablespace=None, auto_created=False, validators=[],
            error_messages=None):
        self.name = name
        self.verbose_name = verbose_name  # May be set by set_attributes_from_name
        self._verbose_name = verbose_name  # Store original for deconstruction
        self.primary_key = primary_key
        self.max_length, self._unique = max_length, unique
        self.blank, self.null = blank, null
        self.rel = rel
        self.default = default
        self.editable = editable
        self.serialize = serialize
        self.unique_for_date = unique_for_date
        self.unique_for_month = unique_for_month
        self.unique_for_year = unique_for_year
        self._choices = choices or []
        self.help_text = help_text
        self.db_column = db_column
        self.db_tablespace = db_tablespace or settings.DEFAULT_INDEX_TABLESPACE
        self.auto_created = auto_created

        # Set db_index to True if the field has a relationship and doesn't
        # explicitly set db_index.
        self.db_index = db_index

        # Adjust the appropriate creation counter, and save our local copy.
        if auto_created:
            self.creation_counter = Field.auto_creation_counter
            Field.auto_creation_counter -= 1
        else:
            self.creation_counter = Field.creation_counter
            Field.creation_counter += 1

        self._validators = validators  # Store for deconstruction later

        messages = {}
        for c in reversed(self.__class__.__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self._error_messages = error_messages  # Store for deconstruction later
        self.error_messages = messages

    def __str__(self):
        """ Return "app_label.model_label.field_name". """
        model = self.model
        app = model._meta.app_label
        return '%s.%s.%s' % (app, model._meta.object_name, self.name)

    def __repr__(self):
        """
        Displays the module, class and name of the field.
        """
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        name = getattr(self, 'name', None)
        if name is not None:
            return '<%s: %s>' % (path, name)
        return '<%s>' % path

    def check(self, **kwargs):
        errors = []
        errors.extend(self._check_field_name())
        errors.extend(self._check_choices())
        errors.extend(self._check_db_index())
        errors.extend(self._check_null_allowed_for_primary_keys())
        errors.extend(self._check_backend_specific_checks(**kwargs))
        return errors

    def _check_field_name(self):
        """ Check if field name is valid, i.e. 1) does not end with an
        underscore, 2) does not contain "__" and 3) is not "pk". """

        if self.name.endswith('_'):
            return [
                checks.Error(
                    'Field names must not end with an underscore.',
                    hint=None,
                    obj=self,
                    id='fields.E001',
                )
            ]
        elif '__' in self.name:
            return [
                checks.Error(
                    'Field names must not contain "__".',
                    hint=None,
                    obj=self,
                    id='fields.E002',
                )
            ]
        elif self.name == 'pk':
            return [
                checks.Error(
                    "'pk' is a reserved word that cannot be used as a field name.",
                    hint=None,
                    obj=self,
                    id='fields.E003',
                )
            ]
        else:
            return []

    def _check_choices(self):
        if self.choices:
            if (isinstance(self.choices, six.string_types) or
                    not is_iterable(self.choices)):
                return [
                    checks.Error(
                        "'choices' must be an iterable (e.g., a list or tuple).",
                        hint=None,
                        obj=self,
                        id='fields.E004',
                    )
                ]
            elif any(isinstance(choice, six.string_types) or
                     not is_iterable(choice) or len(choice) != 2
                     for choice in self.choices):
                return [
                    checks.Error(
                        ("'choices' must be an iterable containing "
                         "(actual value, human readable name) tuples."),
                        hint=None,
                        obj=self,
                        id='fields.E005',
                    )
                ]
            else:
                return []
        else:
            return []

    def _check_db_index(self):
        if self.db_index not in (None, True, False):
            return [
                checks.Error(
                    "'db_index' must be None, True or False.",
                    hint=None,
                    obj=self,
                    id='fields.E006',
                )
            ]
        else:
            return []

    def _check_null_allowed_for_primary_keys(self):
        if (self.primary_key and self.null and
                not connection.features.interprets_empty_strings_as_nulls):
            # We cannot reliably check this for backends like Oracle which
            # consider NULL and '' to be equal (and thus set up
            # character-based fields a little differently).
            return [
                checks.Error(
                    'Primary keys must not have null=True.',
                    hint=('Set null=False on the field, or '
                          'remove primary_key=True argument.'),
                    obj=self,
                    id='fields.E007',
                )
            ]
        else:
            return []

    def _check_backend_specific_checks(self, **kwargs):
        return connection.validation.check_field(self, **kwargs)

    def deconstruct(self):
        """
        Returns enough information to recreate the field as a 4-tuple:

         * The name of the field on the model, if contribute_to_class has been run
         * The import path of the field, including the class: django.db.models.IntegerField
           This should be the most portable version, so less specific may be better.
         * A list of positional arguments
         * A dict of keyword arguments

        Note that the positional or keyword arguments must contain values of the
        following types (including inner values of collection types):

         * None, bool, str, unicode, int, long, float, complex, set, frozenset, list, tuple, dict
         * UUID
         * datetime.datetime (naive), datetime.date
         * top-level classes, top-level functions - will be referenced by their full import path
         * Storage instances - these have their own deconstruct() method

        This is because the values here must be serialized into a text format
        (possibly new Python code, possibly JSON) and these are the only types
        with encoding handlers defined.

        There's no need to return the exact way the field was instantiated this time,
        just ensure that the resulting field is the same - prefer keyword arguments
        over positional ones, and omit parameters with their default values.
        """
        # Short-form way of fetching all the default parameters
        keywords = {}
        possibles = {
            "verbose_name": None,
            "primary_key": False,
            "max_length": None,
            "unique": False,
            "blank": False,
            "null": False,
            "db_index": False,
            "default": NOT_PROVIDED,
            "editable": True,
            "serialize": True,
            "unique_for_date": None,
            "unique_for_month": None,
            "unique_for_year": None,
            "choices": [],
            "help_text": '',
            "db_column": None,
            "db_tablespace": settings.DEFAULT_INDEX_TABLESPACE,
            "auto_created": False,
            "validators": [],
            "error_messages": None,
        }
        attr_overrides = {
            "unique": "_unique",
            "choices": "_choices",
            "error_messages": "_error_messages",
            "validators": "_validators",
            "verbose_name": "_verbose_name",
        }
        equals_comparison = set(["choices", "validators", "db_tablespace"])
        for name, default in possibles.items():
            value = getattr(self, attr_overrides.get(name, name))
            # Unroll anything iterable for choices into a concrete list
            if name == "choices" and isinstance(value, collections.Iterable):
                value = list(value)
            # Do correct kind of comparison
            if name in equals_comparison:
                if value != default:
                    keywords[name] = value
            else:
                if value is not default:
                    keywords[name] = value
        # Work out path - we shorten it for known Django core fields
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        if path.startswith("django.db.models.fields.related"):
            path = path.replace("django.db.models.fields.related", "django.db.models")
        if path.startswith("django.db.models.fields.files"):
            path = path.replace("django.db.models.fields.files", "django.db.models")
        if path.startswith("django.db.models.fields.proxy"):
            path = path.replace("django.db.models.fields.proxy", "django.db.models")
        if path.startswith("django.db.models.fields"):
            path = path.replace("django.db.models.fields", "django.db.models")
        # Return basic info - other fields should override this.
        return (
            force_text(self.name, strings_only=True),
            path,
            [],
            keywords,
        )

    def clone(self):
        """
        Uses deconstruct() to clone a new copy of this Field.
        Will not preserve any class attachments/attribute names.
        """
        name, path, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)

    def __eq__(self, other):
        # Needed for @total_ordering
        if isinstance(other, Field):
            return self.creation_counter == other.creation_counter
        return NotImplemented

    def __lt__(self, other):
        # This is needed because bisect does not take a comparison function.
        if isinstance(other, Field):
            return self.creation_counter < other.creation_counter
        return NotImplemented

    def __hash__(self):
        return hash(self.creation_counter)

    def __deepcopy__(self, memodict):
        # We don't have to deepcopy very much here, since most things are not
        # intended to be altered after initial creation.
        obj = copy.copy(self)
        if self.rel:
            obj.rel = copy.copy(self.rel)
            if hasattr(self.rel, 'field') and self.rel.field is self:
                obj.rel.field = obj
        memodict[id(self)] = obj
        return obj

    def __copy__(self):
        # We need to avoid hitting __reduce__, so define this
        # slightly weird copy construct.
        obj = Empty()
        obj.__class__ = self.__class__
        obj.__dict__ = self.__dict__.copy()
        return obj

    def __reduce__(self):
        """
        Pickling should return the model._meta.fields instance of the field,
        not a new copy of that field. So, we use the app registry to load the
        model and then the field back.
        """
        if not hasattr(self, 'model'):
            # Fields are sometimes used without attaching them to models (for
            # example in aggregation). In this case give back a plain field
            # instance. The code below will create a new empty instance of
            # class self.__class__, then update its dict with self.__dict__
            # values - so, this is very close to normal pickle.
            return _empty, (self.__class__,), self.__dict__
        if self.model._deferred:
            # Deferred model will not be found from the app registry. This
            # could be fixed by reconstructing the deferred model on unpickle.
            raise RuntimeError("Fields of deferred models can't be reduced")
        return _load_field, (self.model._meta.app_label, self.model._meta.object_name,
                             self.name)

    def to_python(self, value):
        """
        Converts the input value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """
        return value

    @cached_property
    def validators(self):
        # Some validators can't be created at field initialization time.
        # This method provides a way to delay their creation until required.
        return self.default_validators + self._validators

    def run_validators(self, value):
        if value in self.empty_values:
            return

        errors = []
        for v in self.validators:
            try:
                v(value)
            except exceptions.ValidationError as e:
                if hasattr(e, 'code') and e.code in self.error_messages:
                    e.message = self.error_messages[e.code]
                errors.extend(e.error_list)

        if errors:
            raise exceptions.ValidationError(errors)

    def validate(self, value, model_instance):
        """
        Validates value and throws ValidationError. Subclasses should override
        this to provide validation logic.
        """
        if not self.editable:
            # Skip validation for non-editable fields.
            return

        if self._choices and value not in self.empty_values:
            for option_key, option_value in self.choices:
                if isinstance(option_value, (list, tuple)):
                    # This is an optgroup, so look inside the group for
                    # options.
                    for optgroup_key, optgroup_value in option_value:
                        if value == optgroup_key:
                            return
                elif value == option_key:
                    return
            raise exceptions.ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'], code='null')

        if not self.blank and value in self.empty_values:
            raise exceptions.ValidationError(self.error_messages['blank'], code='blank')

    def clean(self, value, model_instance):
        """
        Convert the value's type and run validation. Validation errors
        from to_python and validate are propagated. The correct value is
        returned if no error is raised.
        """
        value = self.to_python(value)
        self.validate(value, model_instance)
        self.run_validators(value)
        return value

    def db_type(self, connection):
        """
        Returns the database column data type for this field, for the provided
        connection.
        """
        # The default implementation of this method looks at the
        # backend-specific data_types dictionary, looking up the field by its
        # "internal type".
        #
        # A Field class can implement the get_internal_type() method to specify
        # which *preexisting* Django Field class it's most similar to -- i.e.,
        # a custom field might be represented by a TEXT column type, which is
        # the same as the TextField Django field type, which means the custom
        # field's get_internal_type() returns 'TextField'.
        #
        # But the limitation of the get_internal_type() / data_types approach
        # is that it cannot handle database column types that aren't already
        # mapped to one of the built-in Django field types. In this case, you
        # can implement db_type() instead of get_internal_type() to specify
        # exactly which wacky database column type you want to use.
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        try:
            return connection.creation.data_types[self.get_internal_type()] % data
        except KeyError:
            return None

    def db_parameters(self, connection):
        """
        Extension of db_type(), providing a range of different return
        values (type, checks).
        This will look at db_type(), allowing custom model fields to override it.
        """
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        type_string = self.db_type(connection)
        try:
            check_string = connection.creation.data_type_check_constraints[self.get_internal_type()] % data
        except KeyError:
            check_string = None
        return {
            "type": type_string,
            "check": check_string,
        }

    def db_type_suffix(self, connection):
        return connection.creation.data_types_suffix.get(self.get_internal_type())

    @property
    def unique(self):
        return self._unique or self.primary_key

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name
        self.attname, self.column = self.get_attname_column()
        if self.verbose_name is None and self.name:
            self.verbose_name = self.name.replace('_', ' ')

    def contribute_to_class(self, cls, name, virtual_only=False):
        self.set_attributes_from_name(name)
        self.model = cls
        if virtual_only:
            cls._meta.add_virtual_field(self)
        else:
            cls._meta.add_field(self)
        if self.choices:
            setattr(cls, 'get_%s_display' % self.name,
                    curry(cls._get_FIELD_display, field=self))

    def get_attname(self):
        return self.name

    def get_attname_column(self):
        attname = self.get_attname()
        column = self.db_column or attname
        return attname, column

    def get_cache_name(self):
        return '_%s_cache' % self.name

    def get_internal_type(self):
        return self.__class__.__name__

    def pre_save(self, model_instance, add):
        """
        Returns field's value just before saving.
        """
        return getattr(model_instance, self.attname)

    def get_prep_value(self, value):
        """
        Perform preliminary non-db specific value checks and conversions.
        """
        if isinstance(value, Promise):
            value = value._proxy____cast()
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """Returns field's value prepared for interacting with the database
        backend.

        Used by the default implementations of ``get_db_prep_save``and
        `get_db_prep_lookup```
        """
        if not prepared:
            value = self.get_prep_value(value)
        return value

    def get_db_prep_save(self, value, connection):
        """
        Returns field's value prepared for saving into a database.
        """
        return self.get_db_prep_value(value, connection=connection,
                                      prepared=False)

    def get_prep_lookup(self, lookup_type, value):
        """
        Perform preliminary non-db specific lookup checks and conversions
        """
        if hasattr(value, 'prepare'):
            return value.prepare()
        if hasattr(value, '_prepare'):
            return value._prepare()

        if lookup_type in {
            'iexact', 'contains', 'icontains',
            'startswith', 'istartswith', 'endswith', 'iendswith',
            'month', 'day', 'week_day', 'hour', 'minute', 'second',
            'isnull', 'search', 'regex', 'iregex',
        }:
            return value
        elif lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte'):
            return self.get_prep_value(value)
        elif lookup_type in ('range', 'in'):
            return [self.get_prep_value(v) for v in value]
        elif lookup_type == 'year':
            try:
                return int(value)
            except ValueError:
                raise ValueError("The __year lookup type requires an integer "
                                 "argument")
        return self.get_prep_value(value)

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        """
        Returns field's value prepared for database lookup.
        """
        if not prepared:
            value = self.get_prep_lookup(lookup_type, value)
            prepared = True
        if hasattr(value, 'get_compiler'):
            value = value.get_compiler(connection=connection)
        if hasattr(value, 'as_sql') or hasattr(value, '_as_sql'):
            # If the value has a relabeled_clone method it means the
            # value will be handled later on.
            if hasattr(value, 'relabeled_clone'):
                return value
            if hasattr(value, 'as_sql'):
                sql, params = value.as_sql()
            else:
                sql, params = value._as_sql(connection=connection)
            return QueryWrapper(('(%s)' % sql), params)

        if lookup_type in ('month', 'day', 'week_day', 'hour', 'minute',
                           'second', 'search', 'regex', 'iregex'):
            return [value]
        elif lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte'):
            return [self.get_db_prep_value(value, connection=connection,
                                           prepared=prepared)]
        elif lookup_type in ('range', 'in'):
            return [self.get_db_prep_value(v, connection=connection,
                                           prepared=prepared) for v in value]
        elif lookup_type in ('contains', 'icontains'):
            return ["%%%s%%" % connection.ops.prep_for_like_query(value)]
        elif lookup_type == 'iexact':
            return [connection.ops.prep_for_iexact_query(value)]
        elif lookup_type in ('startswith', 'istartswith'):
            return ["%s%%" % connection.ops.prep_for_like_query(value)]
        elif lookup_type in ('endswith', 'iendswith'):
            return ["%%%s" % connection.ops.prep_for_like_query(value)]
        elif lookup_type == 'isnull':
            return []
        elif lookup_type == 'year':
            if isinstance(self, DateTimeField):
                return connection.ops.year_lookup_bounds_for_datetime_field(value)
            elif isinstance(self, DateField):
                return connection.ops.year_lookup_bounds_for_date_field(value)
            else:
                return [value]          # this isn't supposed to happen
        else:
            return [value]

    def has_default(self):
        """
        Returns a boolean of whether this field has a default value.
        """
        return self.default is not NOT_PROVIDED

    def get_default(self):
        """
        Returns the default value for this field.
        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return force_text(self.default, strings_only=True)
        if (not self.empty_strings_allowed or (self.null and
                   not connection.features.interprets_empty_strings_as_nulls)):
            return None
        return ""

    def get_validator_unique_lookup_type(self):
        return '%s__exact' % self.name

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        """Returns choices with a default blank choices included, for use
        as SelectField choices for this field."""
        blank_defined = False
        choices = list(self.choices) if self.choices else []
        named_groups = choices and isinstance(choices[0][1], (list, tuple))
        if not named_groups:
            for choice, __ in choices:
                if choice in ('', None):
                    blank_defined = True
                    break

        first_choice = (blank_choice if include_blank and
                        not blank_defined else [])
        if self.choices:
            return first_choice + choices
        rel_model = self.rel.to
        if hasattr(self.rel, 'get_related_field'):
            lst = [(getattr(x, self.rel.get_related_field().attname),
                   smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                       self.get_limit_choices_to())]
        else:
            lst = [(x._get_pk_val(), smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                       self.get_limit_choices_to())]
        return first_choice + lst

    def get_choices_default(self):
        return self.get_choices()

    def get_flatchoices(self, include_blank=True,
                        blank_choice=BLANK_CHOICE_DASH):
        """
        Returns flattened choices with a default blank choice included.
        """
        first_choice = blank_choice if include_blank else []
        return first_choice + list(self.flatchoices)

    def _get_val_from_obj(self, obj):
        if obj is not None:
            return getattr(obj, self.attname)
        else:
            return self.get_default()

    def value_to_string(self, obj):
        """
        Returns a string value of this field from the passed obj.
        This is used by the serialization framework.
        """
        return smart_text(self._get_val_from_obj(obj))

    def bind(self, fieldmapping, original, bound_field_class):
        return bound_field_class(self, fieldmapping, original)

    def _get_choices(self):
        if isinstance(self._choices, collections.Iterator):
            choices, self._choices = tee(self._choices)
            return choices
        else:
            return self._choices
    choices = property(_get_choices)

    def _get_flatchoices(self):
        """Flattened version of choices tuple."""
        flat = []
        for choice, value in self.choices:
            if isinstance(value, (list, tuple)):
                flat.extend(value)
            else:
                flat.append((choice, value))
        return flat
    flatchoices = property(_get_flatchoices)

    def save_form_data(self, instance, data):
        setattr(instance, self.name, data)

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        """
        Returns a django.forms.Field instance for this database Field.
        """
        defaults = {'required': not self.blank,
                    'label': capfirst(self.verbose_name),
                    'help_text': self.help_text}
        if self.has_default():
            if callable(self.default):
                defaults['initial'] = self.default
                defaults['show_hidden_initial'] = True
            else:
                defaults['initial'] = self.get_default()
        if self.choices:
            # Fields with choices get special treatment.
            include_blank = (self.blank or
                             not (self.has_default() or 'initial' in kwargs))
            defaults['choices'] = self.get_choices(include_blank=include_blank)
            defaults['coerce'] = self.to_python
            if self.null:
                defaults['empty_value'] = None
            if choices_form_class is not None:
                form_class = choices_form_class
            else:
                form_class = forms.TypedChoiceField
            # Many of the subclass-specific formfield arguments (min_value,
            # max_value) don't apply for choice fields, so be sure to only pass
            # the values that TypedChoiceField will understand.
            for k in list(kwargs):
                if k not in ('coerce', 'empty_value', 'choices', 'required',
                             'widget', 'label', 'initial', 'help_text',
                             'error_messages', 'show_hidden_initial'):
                    del kwargs[k]
        defaults.update(kwargs)
        if form_class is None:
            form_class = forms.CharField
        return form_class(**defaults)

    def value_from_object(self, obj):
        """
        Returns the value of this field in the given model instance.
        """
        return getattr(obj, self.attname)


class AutoField(Field):
    description = _("Integer")

    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be an integer."),
    }

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        super(AutoField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(AutoField, self).check(**kwargs)
        errors.extend(self._check_primary_key())
        return errors

    def _check_primary_key(self):
        if not self.primary_key:
            return [
                checks.Error(
                    'AutoFields must set primary_key=True.',
                    hint=None,
                    obj=self,
                    id='fields.E100',
                ),
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super(AutoField, self).deconstruct()
        del kwargs['blank']
        kwargs['primary_key'] = True
        return name, path, args, kwargs

    def get_internal_type(self):
        return "AutoField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def validate(self, value, model_instance):
        pass

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
            value = connection.ops.validate_autopk_value(value)
        return value

    def get_prep_value(self, value):
        value = super(AutoField, self).get_prep_value(value)
        if value is None:
            return None
        return int(value)

    def contribute_to_class(self, cls, name):
        assert not cls._meta.has_auto_field, \
            "A model can't have more than one AutoField."
        super(AutoField, self).contribute_to_class(cls, name)
        cls._meta.has_auto_field = True
        cls._meta.auto_field = self

    def formfield(self, **kwargs):
        return None


class BooleanField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be either True or False."),
    }
    description = _("Boolean (Either True or False)")

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        super(BooleanField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(BooleanField, self).check(**kwargs)
        errors.extend(self._check_null(**kwargs))
        return errors

    def _check_null(self, **kwargs):
        if getattr(self, 'null', False):
            return [
                checks.Error(
                    'BooleanFields do not accept null values.',
                    hint='Use a NullBooleanField instead.',
                    obj=self,
                    id='fields.E110',
                )
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super(BooleanField, self).deconstruct()
        del kwargs['blank']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "BooleanField"

    def to_python(self, value):
        if value in (True, False):
            # if value is 1 or 0 than it's equal to True or False, but we want
            # to return a true bool for semantic reasons.
            return bool(value)
        if value in ('t', 'True', '1'):
            return True
        if value in ('f', 'False', '0'):
            return False
        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def get_prep_lookup(self, lookup_type, value):
        # Special-case handling for filters coming from a Web request (e.g. the
        # admin interface). Only works for scalar values (not lists). If you're
        # passing in a list, you might as well make things the right type when
        # constructing the list.
        if value in ('1', '0'):
            value = bool(int(value))
        return super(BooleanField, self).get_prep_lookup(lookup_type, value)

    def get_prep_value(self, value):
        value = super(BooleanField, self).get_prep_value(value)
        if value is None:
            return None
        return bool(value)

    def formfield(self, **kwargs):
        # Unlike most fields, BooleanField figures out include_blank from
        # self.null instead of self.blank.
        if self.choices:
            include_blank = (self.null or
                             not (self.has_default() or 'initial' in kwargs))
            defaults = {'choices': self.get_choices(include_blank=include_blank)}
        else:
            defaults = {'form_class': forms.BooleanField}
        defaults.update(kwargs)
        return super(BooleanField, self).formfield(**defaults)


class CharField(Field):
    description = _("String (up to %(max_length)s)")

    def __init__(self, *args, **kwargs):
        super(CharField, self).__init__(*args, **kwargs)
        self.validators.append(validators.MaxLengthValidator(self.max_length))

    def check(self, **kwargs):
        errors = super(CharField, self).check(**kwargs)
        errors.extend(self._check_max_length_attribute(**kwargs))
        return errors

    def _check_max_length_attribute(self, **kwargs):
        try:
            max_length = int(self.max_length)
            if max_length <= 0:
                raise ValueError()
        except TypeError:
            return [
                checks.Error(
                    "CharFields must define a 'max_length' attribute.",
                    hint=None,
                    obj=self,
                    id='fields.E120',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    "'max_length' must be a positive integer.",
                    hint=None,
                    obj=self,
                    id='fields.E121',
                )
            ]
        else:
            return []

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        if isinstance(value, six.string_types) or value is None:
            return value
        return smart_text(value)

    def get_prep_value(self, value):
        value = super(CharField, self).get_prep_value(value)
        return self.to_python(value)

    def formfield(self, **kwargs):
        # Passing max_length to forms.CharField means that the value's length
        # will be validated twice. This is considered acceptable since we want
        # the value in the form field (to pass into widget for example).
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(CharField, self).formfield(**defaults)


# TODO: Maybe move this into contrib, because it's specialized.
class CommaSeparatedIntegerField(CharField):
    default_validators = [validators.validate_comma_separated_integer_list]
    description = _("Comma-separated integers")

    def formfield(self, **kwargs):
        defaults = {
            'error_messages': {
                'invalid': _('Enter only digits separated by commas.'),
            }
        }
        defaults.update(kwargs)
        return super(CommaSeparatedIntegerField, self).formfield(**defaults)


class DateField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid date format. It must be "
                     "in YYYY-MM-DD format."),
        'invalid_date': _("'%(value)s' value has the correct format (YYYY-MM-DD) "
                          "but it is an invalid date."),
    }
    description = _("Date (without time)")

    def __init__(self, verbose_name=None, name=None, auto_now=False,
                 auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
            kwargs['blank'] = True
        super(DateField, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(DateField, self).deconstruct()
        if self.auto_now:
            kwargs['auto_now'] = True
        if self.auto_now_add:
            kwargs['auto_now_add'] = True
        if self.auto_now or self.auto_now_add:
            del kwargs['editable']
            del kwargs['blank']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "DateField"

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            if settings.USE_TZ and timezone.is_aware(value):
                # Convert aware datetimes to the default time zone
                # before casting them to dates (#17742).
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_naive(value, default_timezone)
            return value.date()
        if isinstance(value, datetime.date):
            return value

        try:
            parsed = parse_date(value)
            if parsed is not None:
                return parsed
        except ValueError:
            raise exceptions.ValidationError(
                self.error_messages['invalid_date'],
                code='invalid_date',
                params={'value': value},
            )

        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = datetime.date.today()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(DateField, self).pre_save(model_instance, add)

    def contribute_to_class(self, cls, name):
        super(DateField, self).contribute_to_class(cls, name)
        if not self.null:
            setattr(cls, 'get_next_by_%s' % self.name,
                curry(cls._get_next_or_previous_by_FIELD, field=self,
                      is_next=True))
            setattr(cls, 'get_previous_by_%s' % self.name,
                curry(cls._get_next_or_previous_by_FIELD, field=self,
                      is_next=False))

    def get_prep_lookup(self, lookup_type, value):
        # For dates lookups, convert the value to an int
        # so the database backend always sees a consistent type.
        if lookup_type in ('month', 'day', 'week_day', 'hour', 'minute', 'second'):
            return int(value)
        return super(DateField, self).get_prep_lookup(lookup_type, value)

    def get_prep_value(self, value):
        value = super(DateField, self).get_prep_value(value)
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        # Casts dates into the format expected by the backend
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops.value_to_db_date(value)

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        return '' if val is None else val.isoformat()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateField}
        defaults.update(kwargs)
        return super(DateField, self).formfield(**defaults)


class DateTimeField(DateField):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid format. It must be in "
                     "YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format."),
        'invalid_date': _("'%(value)s' value has the correct format "
                          "(YYYY-MM-DD) but it is an invalid date."),
        'invalid_datetime': _("'%(value)s' value has the correct format "
                              "(YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]) "
                              "but it is an invalid date/time."),
    }
    description = _("Date (with time)")

    # __init__ is inherited from DateField

    def get_internal_type(self):
        return "DateTimeField"

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
            if settings.USE_TZ:
                # For backwards compatibility, interpret naive datetimes in
                # local time. This won't work during DST change, but we can't
                # do much about it, so we let the exceptions percolate up the
                # call stack.
                warnings.warn("DateTimeField %s.%s received a naive datetime "
                              "(%s) while time zone support is active." %
                              (self.model.__name__, self.name, value),
                              RuntimeWarning)
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return value

        try:
            parsed = parse_datetime(value)
            if parsed is not None:
                return parsed
        except ValueError:
            raise exceptions.ValidationError(
                self.error_messages['invalid_datetime'],
                code='invalid_datetime',
                params={'value': value},
            )

        try:
            parsed = parse_date(value)
            if parsed is not None:
                return datetime.datetime(parsed.year, parsed.month, parsed.day)
        except ValueError:
            raise exceptions.ValidationError(
                self.error_messages['invalid_date'],
                code='invalid_date',
                params={'value': value},
            )

        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = timezone.now()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(DateTimeField, self).pre_save(model_instance, add)

    # contribute_to_class is inherited from DateField, it registers
    # get_next_by_FOO and get_prev_by_FOO

    # get_prep_lookup is inherited from DateField

    def get_prep_value(self, value):
        value = super(DateTimeField, self).get_prep_value(value)
        value = self.to_python(value)
        if value is not None and settings.USE_TZ and timezone.is_naive(value):
            # For backwards compatibility, interpret naive datetimes in local
            # time. This won't work during DST change, but we can't do much
            # about it, so we let the exceptions percolate up the call stack.
            try:
                name = '%s.%s' % (self.model.__name__, self.name)
            except AttributeError:
                name = '(unbound)'
            warnings.warn("DateTimeField %s received a naive datetime (%s)"
                          " while time zone support is active." %
                          (name, value),
                          RuntimeWarning)
            default_timezone = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_timezone)
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        # Casts datetimes into the format expected by the backend
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops.value_to_db_datetime(value)

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        return '' if val is None else val.isoformat()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateTimeField}
        defaults.update(kwargs)
        return super(DateTimeField, self).formfield(**defaults)


class DecimalField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be a decimal number."),
    }
    description = _("Decimal number")

    def __init__(self, verbose_name=None, name=None, max_digits=None,
                 decimal_places=None, **kwargs):
        self.max_digits, self.decimal_places = max_digits, decimal_places
        super(DecimalField, self).__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        errors = super(DecimalField, self).check(**kwargs)

        digits_errors = self._check_decimal_places()
        digits_errors.extend(self._check_max_digits())
        if not digits_errors:
            errors.extend(self._check_decimal_places_and_max_digits(**kwargs))
        else:
            errors.extend(digits_errors)
        return errors

    def _check_decimal_places(self):
        try:
            decimal_places = int(self.decimal_places)
            if decimal_places < 0:
                raise ValueError()
        except TypeError:
            return [
                checks.Error(
                    "DecimalFields must define a 'decimal_places' attribute.",
                    hint=None,
                    obj=self,
                    id='fields.E130',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    "'decimal_places' must be a non-negative integer.",
                    hint=None,
                    obj=self,
                    id='fields.E131',
                )
            ]
        else:
            return []

    def _check_max_digits(self):
        try:
            max_digits = int(self.max_digits)
            if max_digits <= 0:
                raise ValueError()
        except TypeError:
            return [
                checks.Error(
                    "DecimalFields must define a 'max_digits' attribute.",
                    hint=None,
                    obj=self,
                    id='fields.E132',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    "'max_digits' must be a positive integer.",
                    hint=None,
                    obj=self,
                    id='fields.E133',
                )
            ]
        else:
            return []

    def _check_decimal_places_and_max_digits(self, **kwargs):
        if int(self.decimal_places) > int(self.max_digits):
            return [
                checks.Error(
                    "'max_digits' must be greater or equal to 'decimal_places'.",
                    hint=None,
                    obj=self,
                    id='fields.E134',
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super(DecimalField, self).deconstruct()
        if self.max_digits is not None:
            kwargs['max_digits'] = self.max_digits
        if self.decimal_places is not None:
            kwargs['decimal_places'] = self.decimal_places
        return name, path, args, kwargs

    def get_internal_type(self):
        return "DecimalField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def _format(self, value):
        if isinstance(value, six.string_types) or value is None:
            return value
        else:
            return self.format_number(value)

    def format_number(self, value):
        """
        Formats a number into a string with the requisite number of digits and
        decimal places.
        """
        # Method moved to django.db.backends.utils.
        #
        # It is preserved because it is used by the oracle backend
        # (django.db.backends.oracle.query), and also for
        # backwards-compatibility with any external code which may have used
        # this method.
        from django.db.backends import utils
        return utils.format_number(value, self.max_digits, self.decimal_places)

    def get_db_prep_save(self, value, connection):
        return connection.ops.value_to_db_decimal(self.to_python(value),
                self.max_digits, self.decimal_places)

    def get_prep_value(self, value):
        value = super(DecimalField, self).get_prep_value(value)
        return self.to_python(value)

    def formfield(self, **kwargs):
        defaults = {
            'max_digits': self.max_digits,
            'decimal_places': self.decimal_places,
            'form_class': forms.DecimalField,
        }
        defaults.update(kwargs)
        return super(DecimalField, self).formfield(**defaults)


class EmailField(CharField):
    default_validators = [validators.validate_email]
    description = _("Email address")

    def __init__(self, *args, **kwargs):
        # max_length should be overridden to 254 characters to be fully
        # compliant with RFCs 3696 and 5321

        kwargs['max_length'] = kwargs.get('max_length', 75)
        super(EmailField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(EmailField, self).deconstruct()
        # We do not exclude max_length if it matches default as we want to change
        # the default in future.
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause email validation to be performed
        # twice.
        defaults = {
            'form_class': forms.EmailField,
        }
        defaults.update(kwargs)
        return super(EmailField, self).formfield(**defaults)


class FilePathField(Field):
    description = _("File path")

    def __init__(self, verbose_name=None, name=None, path='', match=None,
                 recursive=False, allow_files=True, allow_folders=False, **kwargs):
        self.path, self.match, self.recursive = path, match, recursive
        self.allow_files, self.allow_folders = allow_files, allow_folders
        kwargs['max_length'] = kwargs.get('max_length', 100)
        super(FilePathField, self).__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        errors = super(FilePathField, self).check(**kwargs)
        errors.extend(self._check_allowing_files_or_folders(**kwargs))
        return errors

    def _check_allowing_files_or_folders(self, **kwargs):
        if not self.allow_files and not self.allow_folders:
            return [
                checks.Error(
                    "FilePathFields must have either 'allow_files' or 'allow_folders' set to True.",
                    hint=None,
                    obj=self,
                    id='fields.E140',
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super(FilePathField, self).deconstruct()
        if self.path != '':
            kwargs['path'] = self.path
        if self.match is not None:
            kwargs['match'] = self.match
        if self.recursive is not False:
            kwargs['recursive'] = self.recursive
        if self.allow_files is not True:
            kwargs['allow_files'] = self.allow_files
        if self.allow_folders is not False:
            kwargs['allow_folders'] = self.allow_folders
        if kwargs.get("max_length", None) == 100:
            del kwargs["max_length"]
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super(FilePathField, self).get_prep_value(value)
        if value is None:
            return None
        return six.text_type(value)

    def formfield(self, **kwargs):
        defaults = {
            'path': self.path,
            'match': self.match,
            'recursive': self.recursive,
            'form_class': forms.FilePathField,
            'allow_files': self.allow_files,
            'allow_folders': self.allow_folders,
        }
        defaults.update(kwargs)
        return super(FilePathField, self).formfield(**defaults)

    def get_internal_type(self):
        return "FilePathField"


class FloatField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be a float."),
    }
    description = _("Floating point number")

    def get_prep_value(self, value):
        value = super(FloatField, self).get_prep_value(value)
        if value is None:
            return None
        return float(value)

    def get_internal_type(self):
        return "FloatField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.FloatField}
        defaults.update(kwargs)
        return super(FloatField, self).formfield(**defaults)


class IntegerField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be an integer."),
    }
    description = _("Integer")

    @cached_property
    def validators(self):
        # These validators can't be added at field initialization time since
        # they're based on values retrieved from `connection`.
        range_validators = []
        internal_type = self.get_internal_type()
        min_value, max_value = connection.ops.integer_field_range(internal_type)
        if min_value is not None:
            range_validators.append(validators.MinValueValidator(min_value))
        if max_value is not None:
            range_validators.append(validators.MaxValueValidator(max_value))
        return super(IntegerField, self).validators + range_validators

    def get_prep_value(self, value):
        value = super(IntegerField, self).get_prep_value(value)
        if value is None:
            return None
        return int(value)

    def get_prep_lookup(self, lookup_type, value):
        if ((lookup_type == 'gte' or lookup_type == 'lt')
                and isinstance(value, float)):
            value = math.ceil(value)
        return super(IntegerField, self).get_prep_lookup(lookup_type, value)

    def get_internal_type(self):
        return "IntegerField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IntegerField}
        defaults.update(kwargs)
        return super(IntegerField, self).formfield(**defaults)


class BigIntegerField(IntegerField):
    empty_strings_allowed = False
    description = _("Big (8 byte) integer")
    MAX_BIGINT = 9223372036854775807

    def get_internal_type(self):
        return "BigIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': -BigIntegerField.MAX_BIGINT - 1,
                    'max_value': BigIntegerField.MAX_BIGINT}
        defaults.update(kwargs)
        return super(BigIntegerField, self).formfield(**defaults)


class IPAddressField(Field):
    empty_strings_allowed = False
    description = _("IPv4 address")

    def __init__(self, *args, **kwargs):
        warnings.warn("IPAddressField has been deprecated. Use GenericIPAddressField instead.",
                      RemovedInDjango19Warning)
        kwargs['max_length'] = 15
        super(IPAddressField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(IPAddressField, self).deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super(IPAddressField, self).get_prep_value(value)
        if value is None:
            return None
        return six.text_type(value)

    def get_internal_type(self):
        return "IPAddressField"

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IPAddressField}
        defaults.update(kwargs)
        return super(IPAddressField, self).formfield(**defaults)


class GenericIPAddressField(Field):
    empty_strings_allowed = True
    description = _("IP address")
    default_error_messages = {}

    def __init__(self, verbose_name=None, name=None, protocol='both',
                 unpack_ipv4=False, *args, **kwargs):
        self.unpack_ipv4 = unpack_ipv4
        self.protocol = protocol
        self.default_validators, invalid_error_message = \
            validators.ip_address_validators(protocol, unpack_ipv4)
        self.default_error_messages['invalid'] = invalid_error_message
        kwargs['max_length'] = 39
        super(GenericIPAddressField, self).__init__(verbose_name, name, *args,
                                                    **kwargs)

    def check(self, **kwargs):
        errors = super(GenericIPAddressField, self).check(**kwargs)
        errors.extend(self._check_blank_and_null_values(**kwargs))
        return errors

    def _check_blank_and_null_values(self, **kwargs):
        if not getattr(self, 'null', False) and getattr(self, 'blank', False):
            return [
                checks.Error(
                    ('GenericIPAddressFields cannot have blank=True if null=False, '
                     'as blank values are stored as nulls.'),
                    hint=None,
                    obj=self,
                    id='fields.E150',
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super(GenericIPAddressField, self).deconstruct()
        if self.unpack_ipv4 is not False:
            kwargs['unpack_ipv4'] = self.unpack_ipv4
        if self.protocol != "both":
            kwargs['protocol'] = self.protocol
        if kwargs.get("max_length", None) == 39:
            del kwargs['max_length']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "GenericIPAddressField"

    def to_python(self, value):
        if value and ':' in value:
            return clean_ipv6_address(value,
                self.unpack_ipv4, self.error_messages['invalid'])
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return value or None

    def get_prep_value(self, value):
        value = super(GenericIPAddressField, self).get_prep_value(value)
        if value is None:
            return None
        if value and ':' in value:
            try:
                return clean_ipv6_address(value, self.unpack_ipv4)
            except exceptions.ValidationError:
                pass
        return six.text_type(value)

    def formfield(self, **kwargs):
        defaults = {
            'protocol': self.protocol,
            'form_class': forms.GenericIPAddressField,
        }
        defaults.update(kwargs)
        return super(GenericIPAddressField, self).formfield(**defaults)


class NullBooleanField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be either None, True or False."),
    }
    description = _("Boolean (Either True, False or None)")

    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        kwargs['blank'] = True
        super(NullBooleanField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(NullBooleanField, self).deconstruct()
        del kwargs['null']
        del kwargs['blank']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "NullBooleanField"

    def to_python(self, value):
        if value is None:
            return None
        if value in (True, False):
            return bool(value)
        if value in ('None',):
            return None
        if value in ('t', 'True', '1'):
            return True
        if value in ('f', 'False', '0'):
            return False
        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def get_prep_lookup(self, lookup_type, value):
        # Special-case handling for filters coming from a Web request (e.g. the
        # admin interface). Only works for scalar values (not lists). If you're
        # passing in a list, you might as well make things the right type when
        # constructing the list.
        if value in ('1', '0'):
            value = bool(int(value))
        return super(NullBooleanField, self).get_prep_lookup(lookup_type,
                                                             value)

    def get_prep_value(self, value):
        value = super(NullBooleanField, self).get_prep_value(value)
        if value is None:
            return None
        return bool(value)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.NullBooleanField,
            'required': not self.blank,
            'label': capfirst(self.verbose_name),
            'help_text': self.help_text}
        defaults.update(kwargs)
        return super(NullBooleanField, self).formfield(**defaults)


class PositiveIntegerField(IntegerField):
    description = _("Positive integer")

    def get_internal_type(self):
        return "PositiveIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0}
        defaults.update(kwargs)
        return super(PositiveIntegerField, self).formfield(**defaults)


class PositiveSmallIntegerField(IntegerField):
    description = _("Positive small integer")

    def get_internal_type(self):
        return "PositiveSmallIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0}
        defaults.update(kwargs)
        return super(PositiveSmallIntegerField, self).formfield(**defaults)


class SlugField(CharField):
    default_validators = [validators.validate_slug]
    description = _("Slug (up to %(max_length)s)")

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 50)
        # Set db_index=True unless it's been set manually.
        if 'db_index' not in kwargs:
            kwargs['db_index'] = True
        super(SlugField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(SlugField, self).deconstruct()
        if kwargs.get("max_length", None) == 50:
            del kwargs['max_length']
        if self.db_index is False:
            kwargs['db_index'] = False
        else:
            del kwargs['db_index']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "SlugField"

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.SlugField}
        defaults.update(kwargs)
        return super(SlugField, self).formfield(**defaults)


class SmallIntegerField(IntegerField):
    description = _("Small integer")

    def get_internal_type(self):
        return "SmallIntegerField"


class TextField(Field):
    description = _("Text")

    def get_internal_type(self):
        return "TextField"

    def get_prep_value(self, value):
        value = super(TextField, self).get_prep_value(value)
        if isinstance(value, six.string_types) or value is None:
            return value
        return smart_text(value)

    def formfield(self, **kwargs):
        # Passing max_length to forms.CharField means that the value's length
        # will be validated twice. This is considered acceptable since we want
        # the value in the form field (to pass into widget for example).
        defaults = {'max_length': self.max_length, 'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(TextField, self).formfield(**defaults)


class TimeField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid format. It must be in "
                     "HH:MM[:ss[.uuuuuu]] format."),
        'invalid_time': _("'%(value)s' value has the correct format "
                          "(HH:MM[:ss[.uuuuuu]]) but it is an invalid time."),
    }
    description = _("Time")

    def __init__(self, verbose_name=None, name=None, auto_now=False,
                 auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
            kwargs['blank'] = True
        super(TimeField, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(TimeField, self).deconstruct()
        if self.auto_now is not False:
            kwargs["auto_now"] = self.auto_now
        if self.auto_now_add is not False:
            kwargs["auto_now_add"] = self.auto_now_add
        if self.auto_now or self.auto_now_add:
            del kwargs['blank']
            del kwargs['editable']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "TimeField"

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        if isinstance(value, datetime.datetime):
            # Not usually a good idea to pass in a datetime here (it loses
            # information), but this can be a side-effect of interacting with a
            # database backend (e.g. Oracle), so we'll be accommodating.
            return value.time()

        try:
            parsed = parse_time(value)
            if parsed is not None:
                return parsed
        except ValueError:
            raise exceptions.ValidationError(
                self.error_messages['invalid_time'],
                code='invalid_time',
                params={'value': value},
            )

        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = datetime.datetime.now().time()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(TimeField, self).pre_save(model_instance, add)

    def get_prep_value(self, value):
        value = super(TimeField, self).get_prep_value(value)
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        # Casts times into the format expected by the backend
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops.value_to_db_time(value)

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        return '' if val is None else val.isoformat()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.TimeField}
        defaults.update(kwargs)
        return super(TimeField, self).formfield(**defaults)


class URLField(CharField):
    default_validators = [validators.URLValidator()]
    description = _("URL")

    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        super(URLField, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(URLField, self).deconstruct()
        if kwargs.get("max_length", None) == 200:
            del kwargs['max_length']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause URL validation to be performed
        # twice.
        defaults = {
            'form_class': forms.URLField,
        }
        defaults.update(kwargs)
        return super(URLField, self).formfield(**defaults)


class BinaryField(Field):
    description = _("Raw binary data")
    empty_values = [None, b'']

    def __init__(self, *args, **kwargs):
        kwargs['editable'] = False
        super(BinaryField, self).__init__(*args, **kwargs)
        if self.max_length is not None:
            self.validators.append(validators.MaxLengthValidator(self.max_length))

    def deconstruct(self):
        name, path, args, kwargs = super(BinaryField, self).deconstruct()
        del kwargs['editable']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "BinaryField"

    def get_default(self):
        if self.has_default() and not callable(self.default):
            return self.default
        default = super(BinaryField, self).get_default()
        if default == '':
            return b''
        return default

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super(BinaryField, self).get_db_prep_value(value, connection, prepared)
        if value is not None:
            return connection.Database.Binary(value)
        return value

    def value_to_string(self, obj):
        """Binary data is serialized as base64"""
        return b64encode(force_bytes(self._get_val_from_obj(obj))).decode('ascii')

    def to_python(self, value):
        # If it's a string, it should be base64-encoded data
        if isinstance(value, six.text_type):
            return six.memoryview(b64decode(force_bytes(value)))
        return value
