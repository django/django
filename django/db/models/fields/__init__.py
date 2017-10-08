import collections
import copy
import datetime
import decimal
import itertools
import uuid
import warnings
from base64 import b64decode, b64encode
from functools import partialmethod, total_ordering

from django import forms
from django.apps import apps
from django.conf import settings
from django.core import checks, exceptions, validators
# When the _meta object was formalized, this exception was moved to
# django.core.exceptions. It is retained here for backwards compatibility
# purposes.
from django.core.exceptions import FieldDoesNotExist  # NOQA
from django.db import connection, connections, router
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query_utils import DeferredAttribute, RegisterLookupMixin
from django.utils import timezone
from django.utils.datastructures import DictWrapper
from django.utils.dateparse import (
    parse_date, parse_datetime, parse_duration, parse_time,
)
from django.utils.duration import duration_string
from django.utils.encoding import force_bytes, smart_text
from django.utils.functional import Promise, cached_property
from django.utils.ipv6 import clean_ipv6_address
from django.utils.itercompat import is_iterable
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

__all__ = [
    'AutoField', 'BLANK_CHOICE_DASH', 'BigAutoField', 'BigIntegerField',
    'BinaryField', 'BooleanField', 'CharField', 'CommaSeparatedIntegerField',
    'DateField', 'DateTimeField', 'DecimalField', 'DurationField',
    'EmailField', 'Empty', 'Field', 'FieldDoesNotExist', 'FilePathField',
    'FloatField', 'GenericIPAddressField', 'IPAddressField', 'IntegerField',
    'NOT_PROVIDED', 'NullBooleanField', 'PositiveIntegerField',
    'PositiveSmallIntegerField', 'SlugField', 'SmallIntegerField', 'TextField',
    'TimeField', 'URLField', 'UUIDField',
]


class Empty:
    pass


class NOT_PROVIDED:
    pass


# The values to use for "blank" in SelectFields. Will be appended to the start
# of most "choices" lists.
BLANK_CHOICE_DASH = [("", "---------")]


def _load_field(app_label, model_name, field_name):
    return apps.get_model(app_label, model_name)._meta.get_field(field_name)


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


def return_None():
    return None


@total_ordering
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
    system_check_deprecated_details = None
    system_check_removed_details = None

    # Field flags
    hidden = False

    many_to_many = None
    many_to_one = None
    one_to_many = None
    one_to_one = None
    related_model = None

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
                 db_tablespace=None, auto_created=False, validators=(),
                 error_messages=None):
        self.name = name
        self.verbose_name = verbose_name  # May be set by set_attributes_from_name
        self._verbose_name = verbose_name  # Store original for deconstruction
        self.primary_key = primary_key
        self.max_length, self._unique = max_length, unique
        self.blank, self.null = blank, null
        self.remote_field = rel
        self.is_relation = self.remote_field is not None
        self.default = default
        self.editable = editable
        self.serialize = serialize
        self.unique_for_date = unique_for_date
        self.unique_for_month = unique_for_month
        self.unique_for_year = unique_for_year
        if isinstance(choices, collections.Iterator):
            choices = list(choices)
        self.choices = choices or []
        self.help_text = help_text
        self.db_index = db_index
        self.db_column = db_column
        self._db_tablespace = db_tablespace
        self.auto_created = auto_created

        # Adjust the appropriate creation counter, and save our local copy.
        if auto_created:
            self.creation_counter = Field.auto_creation_counter
            Field.auto_creation_counter -= 1
        else:
            self.creation_counter = Field.creation_counter
            Field.creation_counter += 1

        self._validators = list(validators)  # Store for deconstruction later

        messages = {}
        for c in reversed(self.__class__.__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self._error_messages = error_messages  # Store for deconstruction later
        self.error_messages = messages

    def __str__(self):
        """
        Return "app_label.model_label.field_name" for fields attached to
        models.
        """
        if not hasattr(self, 'model'):
            return super().__str__()
        model = self.model
        app = model._meta.app_label
        return '%s.%s.%s' % (app, model._meta.object_name, self.name)

    def __repr__(self):
        """Display the module, class, and name of the field."""
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__qualname__)
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
        errors.extend(self._check_validators())
        errors.extend(self._check_deprecation_details())
        return errors

    def _check_field_name(self):
        """
        Check if field name is valid, i.e. 1) does not end with an
        underscore, 2) does not contain "__" and 3) is not "pk".
        """
        if self.name.endswith('_'):
            return [
                checks.Error(
                    'Field names must not end with an underscore.',
                    obj=self,
                    id='fields.E001',
                )
            ]
        elif LOOKUP_SEP in self.name:
            return [
                checks.Error(
                    'Field names must not contain "%s".' % (LOOKUP_SEP,),
                    obj=self,
                    id='fields.E002',
                )
            ]
        elif self.name == 'pk':
            return [
                checks.Error(
                    "'pk' is a reserved word that cannot be used as a field name.",
                    obj=self,
                    id='fields.E003',
                )
            ]
        else:
            return []

    def _check_choices(self):
        if self.choices:
            if isinstance(self.choices, str) or not is_iterable(self.choices):
                return [
                    checks.Error(
                        "'choices' must be an iterable (e.g., a list or tuple).",
                        obj=self,
                        id='fields.E004',
                    )
                ]
            elif any(isinstance(choice, str) or
                     not is_iterable(choice) or len(choice) != 2
                     for choice in self.choices):
                return [
                    checks.Error(
                        "'choices' must be an iterable containing "
                        "(actual value, human readable name) tuples.",
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
        app_label = self.model._meta.app_label
        for db in connections:
            if router.allow_migrate(db, app_label, model_name=self.model._meta.model_name):
                return connections[db].validation.check_field(self, **kwargs)
        return []

    def _check_validators(self):
        errors = []
        for i, validator in enumerate(self.validators):
            if not callable(validator):
                errors.append(
                    checks.Error(
                        "All 'validators' must be callable.",
                        hint=(
                            "validators[{i}] ({repr}) isn't a function or "
                            "instance of a validator class.".format(
                                i=i, repr=repr(validator),
                            )
                        ),
                        obj=self,
                        id='fields.E008',
                    )
                )
        return errors

    def _check_deprecation_details(self):
        if self.system_check_removed_details is not None:
            return [
                checks.Error(
                    self.system_check_removed_details.get(
                        'msg',
                        '%s has been removed except for support in historical '
                        'migrations.' % self.__class__.__name__
                    ),
                    hint=self.system_check_removed_details.get('hint'),
                    obj=self,
                    id=self.system_check_removed_details.get('id', 'fields.EXXX'),
                )
            ]
        elif self.system_check_deprecated_details is not None:
            return [
                checks.Warning(
                    self.system_check_deprecated_details.get(
                        'msg',
                        '%s has been deprecated.' % self.__class__.__name__
                    ),
                    hint=self.system_check_deprecated_details.get('hint'),
                    obj=self,
                    id=self.system_check_deprecated_details.get('id', 'fields.WXXX'),
                )
            ]
        return []

    def get_col(self, alias, output_field=None):
        if output_field is None:
            output_field = self
        if alias != self.model._meta.db_table or output_field != self:
            from django.db.models.expressions import Col
            return Col(alias, self, output_field)
        else:
            return self.cached_col

    @cached_property
    def cached_col(self):
        from django.db.models.expressions import Col
        return Col(self.model._meta.db_table, self)

    def select_format(self, compiler, sql, params):
        """
        Custom format for select clauses. For example, GIS columns need to be
        selected as AsText(table.col) on MySQL as the table.col data can't be
        used by Django.
        """
        return sql, params

    def deconstruct(self):
        """
        Return enough information to recreate the field as a 4-tuple:

         * The name of the field on the model, if contribute_to_class() has
           been run.
         * The import path of the field, including the class:e.g.
           django.db.models.IntegerField This should be the most portable
           version, so less specific may be better.
         * A list of positional arguments.
         * A dict of keyword arguments.

        Note that the positional or keyword arguments must contain values of
        the following types (including inner values of collection types):

         * None, bool, str, int, float, complex, set, frozenset, list, tuple,
           dict
         * UUID
         * datetime.datetime (naive), datetime.date
         * top-level classes, top-level functions - will be referenced by their
           full import path
         * Storage instances - these have their own deconstruct() method

        This is because the values here must be serialized into a text format
        (possibly new Python code, possibly JSON) and these are the only types
        with encoding handlers defined.

        There's no need to return the exact way the field was instantiated this
        time, just ensure that the resulting field is the same - prefer keyword
        arguments over positional ones, and omit parameters with their default
        values.
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
            "db_tablespace": None,
            "auto_created": False,
            "validators": [],
            "error_messages": None,
        }
        attr_overrides = {
            "unique": "_unique",
            "error_messages": "_error_messages",
            "validators": "_validators",
            "verbose_name": "_verbose_name",
            "db_tablespace": "_db_tablespace",
        }
        equals_comparison = {"choices", "validators"}
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
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__qualname__)
        if path.startswith("django.db.models.fields.related"):
            path = path.replace("django.db.models.fields.related", "django.db.models")
        if path.startswith("django.db.models.fields.files"):
            path = path.replace("django.db.models.fields.files", "django.db.models")
        if path.startswith("django.db.models.fields.proxy"):
            path = path.replace("django.db.models.fields.proxy", "django.db.models")
        if path.startswith("django.db.models.fields"):
            path = path.replace("django.db.models.fields", "django.db.models")
        # Return basic info - other fields should override this.
        return (self.name, path, [], keywords)

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
        if self.remote_field:
            obj.remote_field = copy.copy(self.remote_field)
            if hasattr(self.remote_field, 'field') and self.remote_field.field is self:
                obj.remote_field.field = obj
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
        not a new copy of that field. So, use the app registry to load the
        model and then the field back.
        """
        if not hasattr(self, 'model'):
            # Fields are sometimes used without attaching them to models (for
            # example in aggregation). In this case give back a plain field
            # instance. The code below will create a new empty instance of
            # class self.__class__, then update its dict with self.__dict__
            # values - so, this is very close to normal pickle.
            state = self.__dict__.copy()
            # The _get_default cached_property can't be pickled due to lambda
            # usage.
            state.pop('_get_default', None)
            return _empty, (self.__class__,), state
        return _load_field, (self.model._meta.app_label, self.model._meta.object_name,
                             self.name)

    def get_pk_value_on_save(self, instance):
        """
        Hook to generate new PK values on save. This method is called when
        saving instances with no primary key value set. If this method returns
        something else than None, then the returned value is used when saving
        the new instance.
        """
        if self.default:
            return self.get_default()
        return None

    def to_python(self, value):
        """
        Convert the input value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Return the converted value. Subclasses should override this.
        """
        return value

    @cached_property
    def validators(self):
        """
        Some validators can't be created at field initialization time.
        This method provides a way to delay their creation until required.
        """
        return list(itertools.chain(self.default_validators, self._validators))

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
        Validate value and raise ValidationError if necessary. Subclasses
        should override this to provide validation logic.
        """
        if not self.editable:
            # Skip validation for non-editable fields.
            return

        if self.choices and value not in self.empty_values:
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
        from to_python() and validate() are propagated. Return the correct
        value if no error is raised.
        """
        value = self.to_python(value)
        self.validate(value, model_instance)
        self.run_validators(value)
        return value

    def db_type_parameters(self, connection):
        return DictWrapper(self.__dict__, connection.ops.quote_name, 'qn_')

    def db_check(self, connection):
        """
        Return the database column check constraint for this field, for the
        provided connection. Works the same way as db_type() for the case that
        get_internal_type() does not map to a preexisting model field.
        """
        data = self.db_type_parameters(connection)
        try:
            return connection.data_type_check_constraints[self.get_internal_type()] % data
        except KeyError:
            return None

    def db_type(self, connection):
        """
        Return the database column data type for this field, for the provided
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
        data = self.db_type_parameters(connection)
        try:
            return connection.data_types[self.get_internal_type()] % data
        except KeyError:
            return None

    def rel_db_type(self, connection):
        """
        Return the data type that a related field pointing to this field should
        use. For example, this method is called by ForeignKey and OneToOneField
        to determine its data type.
        """
        return self.db_type(connection)

    def cast_db_type(self, connection):
        """Return the data type to use in the Cast() function."""
        db_type = connection.ops.cast_data_types.get(self.get_internal_type())
        if db_type:
            return db_type % self.db_type_parameters(connection)
        return self.db_type(connection)

    def db_parameters(self, connection):
        """
        Extension of db_type(), providing a range of different return values
        (type, checks). This will look at db_type(), allowing custom model
        fields to override it.
        """
        type_string = self.db_type(connection)
        check_string = self.db_check(connection)
        return {
            "type": type_string,
            "check": check_string,
        }

    def db_type_suffix(self, connection):
        return connection.data_types_suffix.get(self.get_internal_type())

    def get_db_converters(self, connection):
        if hasattr(self, 'from_db_value'):
            return [self.from_db_value]
        return []

    @property
    def unique(self):
        return self._unique or self.primary_key

    @property
    def db_tablespace(self):
        return self._db_tablespace or settings.DEFAULT_INDEX_TABLESPACE

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name
        self.attname, self.column = self.get_attname_column()
        self.concrete = self.column is not None
        if self.verbose_name is None and self.name:
            self.verbose_name = self.name.replace('_', ' ')

    def contribute_to_class(self, cls, name, private_only=False):
        """
        Register the field with the model class it belongs to.

        If private_only is True, create a separate instance of this field
        for every subclass of cls, even if cls is not an abstract model.
        """
        self.set_attributes_from_name(name)
        self.model = cls
        if private_only:
            cls._meta.add_field(self, private=True)
        else:
            cls._meta.add_field(self)
        if self.column:
            # Don't override classmethods with the descriptor. This means that
            # if you have a classmethod and a field with the same name, then
            # such fields can't be deferred (we don't have a check for this).
            if not getattr(cls, self.attname, None):
                setattr(cls, self.attname, DeferredAttribute(self.attname, cls))
        if self.choices:
            setattr(cls, 'get_%s_display' % self.name,
                    partialmethod(cls._get_FIELD_display, field=self))

    def get_filter_kwargs_for_object(self, obj):
        """
        Return a dict that when passed as kwargs to self.model.filter(), would
        yield all instances having the same value for this field as obj has.
        """
        return {self.name: getattr(obj, self.attname)}

    def get_attname(self):
        return self.name

    def get_attname_column(self):
        attname = self.get_attname()
        column = self.db_column or attname
        return attname, column

    def get_internal_type(self):
        return self.__class__.__name__

    def pre_save(self, model_instance, add):
        """Return field's value just before saving."""
        return getattr(model_instance, self.attname)

    def get_prep_value(self, value):
        """Perform preliminary non-db specific value checks and conversions."""
        if isinstance(value, Promise):
            value = value._proxy____cast()
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        """
        Return field's value prepared for interacting with the database backend.

        Used by the default implementations of get_db_prep_save().
        """
        if not prepared:
            value = self.get_prep_value(value)
        return value

    def get_db_prep_save(self, value, connection):
        """Return field's value prepared for saving into a database."""
        return self.get_db_prep_value(value, connection=connection, prepared=False)

    def has_default(self):
        """Return a boolean of whether this field has a default value."""
        return self.default is not NOT_PROVIDED

    def get_default(self):
        """Return the default value for this field."""
        return self._get_default()

    @cached_property
    def _get_default(self):
        if self.has_default():
            if callable(self.default):
                return self.default
            return lambda: self.default

        if not self.empty_strings_allowed or self.null and not connection.features.interprets_empty_strings_as_nulls:
            return return_None
        return str  # return empty string

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None):
        """
        Return choices with a default blank choices included, for use
        as <select> choices for this field.
        """
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
        rel_model = self.remote_field.model
        limit_choices_to = limit_choices_to or self.get_limit_choices_to()
        if hasattr(self.remote_field, 'get_related_field'):
            lst = [(getattr(x, self.remote_field.get_related_field().attname),
                   smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                       limit_choices_to)]
        else:
            lst = [(x.pk, smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                       limit_choices_to)]
        return first_choice + lst

    def value_to_string(self, obj):
        """
        Return a string value of this field from the passed obj.
        This is used by the serialization framework.
        """
        return str(self.value_from_object(obj))

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
        """Return a django.forms.Field instance for this field."""
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
                             'error_messages', 'show_hidden_initial', 'disabled'):
                    del kwargs[k]
        defaults.update(kwargs)
        if form_class is None:
            form_class = forms.CharField
        return form_class(**defaults)

    def value_from_object(self, obj):
        """Return the value of this field in the given model instance."""
        return getattr(obj, self.attname)


class AutoField(Field):
    description = _("Integer")

    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be an integer."),
    }

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        super().__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_primary_key())
        return errors

    def _check_primary_key(self):
        if not self.primary_key:
            return [
                checks.Error(
                    'AutoFields must set primary_key=True.',
                    obj=self,
                    id='fields.E100',
                ),
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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

    def rel_db_type(self, connection):
        return IntegerField().db_type(connection=connection)

    def validate(self, value, model_instance):
        pass

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
            value = connection.ops.validate_autopk_value(value)
        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return int(value)

    def contribute_to_class(self, cls, name, **kwargs):
        assert not cls._meta.auto_field, "A model can't have more than one AutoField."
        super().contribute_to_class(cls, name, **kwargs)
        cls._meta.auto_field = self

    def formfield(self, **kwargs):
        return None


class BigAutoField(AutoField):
    description = _("Big (8 byte) integer")

    def get_internal_type(self):
        return "BigAutoField"

    def rel_db_type(self, connection):
        return BigIntegerField().db_type(connection=connection)


class BooleanField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be either True or False."),
    }
    description = _("Boolean (Either True or False)")

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        super().__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
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
        name, path, args, kwargs = super().deconstruct()
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

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return self.to_python(value)

    def formfield(self, **kwargs):
        # Unlike most fields, BooleanField figures out include_blank from
        # self.null instead of self.blank.
        if self.choices:
            include_blank = not (self.has_default() or 'initial' in kwargs)
            defaults = {'choices': self.get_choices(include_blank=include_blank)}
        else:
            defaults = {'form_class': forms.BooleanField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class CharField(Field):
    description = _("String (up to %(max_length)s)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(validators.MaxLengthValidator(self.max_length))

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_max_length_attribute(**kwargs))
        return errors

    def _check_max_length_attribute(self, **kwargs):
        if self.max_length is None:
            return [
                checks.Error(
                    "CharFields must define a 'max_length' attribute.",
                    obj=self,
                    id='fields.E120',
                )
            ]
        elif (not isinstance(self.max_length, int) or isinstance(self.max_length, bool) or
                self.max_length <= 0):
            return [
                checks.Error(
                    "'max_length' must be a positive integer.",
                    obj=self,
                    id='fields.E121',
                )
            ]
        else:
            return []

    def cast_db_type(self, connection):
        if self.max_length is None:
            return connection.ops.cast_char_field_without_max_length
        return super().cast_db_type(connection)

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return str(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.to_python(value)

    def formfield(self, **kwargs):
        # Passing max_length to forms.CharField means that the value's length
        # will be validated twice. This is considered acceptable since we want
        # the value in the form field (to pass into widget for example).
        defaults = {'max_length': self.max_length}
        # TODO: Handle multiple backends with different feature flags.
        if self.null and not connection.features.interprets_empty_strings_as_nulls:
            defaults['empty_value'] = None
        defaults.update(kwargs)
        return super().formfield(**defaults)


class CommaSeparatedIntegerField(CharField):
    default_validators = [validators.validate_comma_separated_integer_list]
    description = _("Comma-separated integers")
    system_check_removed_details = {
        'msg': (
            'CommaSeparatedIntegerField is removed except for support in '
            'historical migrations.'
        ),
        'hint': (
            'Use CharField(validators=[validate_comma_separated_integer_list]) '
            'instead.'
        ),
        'id': 'fields.E901',
    }


class DateTimeCheckMixin:

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_mutually_exclusive_options())
        errors.extend(self._check_fix_default_value())
        return errors

    def _check_mutually_exclusive_options(self):
        # auto_now, auto_now_add, and default are mutually exclusive
        # options. The use of more than one of these options together
        # will trigger an Error
        mutually_exclusive_options = [self.auto_now_add, self.auto_now, self.has_default()]
        enabled_options = [option not in (None, False) for option in mutually_exclusive_options].count(True)
        if enabled_options > 1:
            return [
                checks.Error(
                    "The options auto_now, auto_now_add, and default "
                    "are mutually exclusive. Only one of these options "
                    "may be present.",
                    obj=self,
                    id='fields.E160',
                )
            ]
        else:
            return []

    def _check_fix_default_value(self):
        return []


class DateField(DateTimeCheckMixin, Field):
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
        super().__init__(verbose_name, name, **kwargs)

    def _check_fix_default_value(self):
        """
        Warn that using an actual date or datetime value is probably wrong;
        it's only evaluated on server startup.
        """
        if not self.has_default():
            return []

        now = timezone.now()
        if not timezone.is_naive(now):
            now = timezone.make_naive(now, timezone.utc)
        value = self.default
        if isinstance(value, datetime.datetime):
            if not timezone.is_naive(value):
                value = timezone.make_naive(value, timezone.utc)
            value = value.date()
        elif isinstance(value, datetime.date):
            # Nothing to do, as dates don't have tz information
            pass
        else:
            # No explicit date / datetime value -- no checks necessary
            return []
        offset = datetime.timedelta(days=1)
        lower = (now - offset).date()
        upper = (now + offset).date()
        if lower <= value <= upper:
            return [
                checks.Warning(
                    'Fixed default value provided.',
                    hint='It seems you set a fixed date / time / datetime '
                         'value as default for this field. This may not be '
                         'what you want. If you want to have the current date '
                         'as default, use `django.utils.timezone.now`',
                    obj=self,
                    id='fields.W161',
                )
            ]

        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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
            return super().pre_save(model_instance, add)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        if not self.null:
            setattr(
                cls, 'get_next_by_%s' % self.name,
                partialmethod(cls._get_next_or_previous_by_FIELD, field=self, is_next=True)
            )
            setattr(
                cls, 'get_previous_by_%s' % self.name,
                partialmethod(cls._get_next_or_previous_by_FIELD, field=self, is_next=False)
            )

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        # Casts dates into the format expected by the backend
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops.adapt_datefield_value(value)

    def value_to_string(self, obj):
        val = self.value_from_object(obj)
        return '' if val is None else val.isoformat()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


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

    def _check_fix_default_value(self):
        """
        Warn that using an actual date or datetime value is probably wrong;
        it's only evaluated on server startup.
        """
        if not self.has_default():
            return []

        now = timezone.now()
        if not timezone.is_naive(now):
            now = timezone.make_naive(now, timezone.utc)
        value = self.default
        if isinstance(value, datetime.datetime):
            second_offset = datetime.timedelta(seconds=10)
            lower = now - second_offset
            upper = now + second_offset
            if timezone.is_aware(value):
                value = timezone.make_naive(value, timezone.utc)
        elif isinstance(value, datetime.date):
            second_offset = datetime.timedelta(seconds=10)
            lower = now - second_offset
            lower = datetime.datetime(lower.year, lower.month, lower.day)
            upper = now + second_offset
            upper = datetime.datetime(upper.year, upper.month, upper.day)
            value = datetime.datetime(value.year, value.month, value.day)
        else:
            # No explicit date / datetime value -- no checks necessary
            return []
        if lower <= value <= upper:
            return [
                checks.Warning(
                    'Fixed default value provided.',
                    hint='It seems you set a fixed date / time / datetime '
                         'value as default for this field. This may not be '
                         'what you want. If you want to have the current date '
                         'as default, use `django.utils.timezone.now`',
                    obj=self,
                    id='fields.W161',
                )
            ]

        return []

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
            return super().pre_save(model_instance, add)

    # contribute_to_class is inherited from DateField, it registers
    # get_next_by_FOO and get_prev_by_FOO

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
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
        return connection.ops.adapt_datetimefield_value(value)

    def value_to_string(self, obj):
        val = self.value_from_object(obj)
        return '' if val is None else val.isoformat()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateTimeField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class DecimalField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be a decimal number."),
    }
    description = _("Decimal number")

    def __init__(self, verbose_name=None, name=None, max_digits=None,
                 decimal_places=None, **kwargs):
        self.max_digits, self.decimal_places = max_digits, decimal_places
        super().__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        errors = super().check(**kwargs)

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
                    obj=self,
                    id='fields.E130',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    "'decimal_places' must be a non-negative integer.",
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
                    obj=self,
                    id='fields.E132',
                )
            ]
        except ValueError:
            return [
                checks.Error(
                    "'max_digits' must be a positive integer.",
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
                    obj=self,
                    id='fields.E134',
                )
            ]
        return []

    @cached_property
    def validators(self):
        return super().validators + [
            validators.DecimalValidator(self.max_digits, self.decimal_places)
        ]

    @cached_property
    def context(self):
        return decimal.Context(prec=self.max_digits)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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
        if isinstance(value, float):
            return self.context.create_decimal_from_float(value)
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def format_number(self, value):
        """
        Format a number into a string with the requisite number of digits and
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
        return connection.ops.adapt_decimalfield_value(self.to_python(value), self.max_digits, self.decimal_places)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.to_python(value)

    def formfield(self, **kwargs):
        defaults = {
            'max_digits': self.max_digits,
            'decimal_places': self.decimal_places,
            'form_class': forms.DecimalField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class DurationField(Field):
    """
    Store timedelta objects.

    Use interval on PostgreSQL, INTERVAL DAY TO SECOND on Oracle, and bigint
    of microseconds on other databases.
    """
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid format. It must be in "
                     "[DD] [HH:[MM:]]ss[.uuuuuu] format.")
    }
    description = _("Duration")

    def get_internal_type(self):
        return "DurationField"

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.timedelta):
            return value
        try:
            parsed = parse_duration(value)
        except ValueError:
            pass
        else:
            if parsed is not None:
                return parsed

        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def get_db_prep_value(self, value, connection, prepared=False):
        if connection.features.has_native_duration_field:
            return value
        if value is None:
            return None
        # Discard any fractional microseconds due to floating point arithmetic.
        return round(value.total_seconds() * 1000000)

    def get_db_converters(self, connection):
        converters = []
        if not connection.features.has_native_duration_field:
            converters.append(connection.ops.convert_durationfield_value)
        return converters + super().get_db_converters(connection)

    def value_to_string(self, obj):
        val = self.value_from_object(obj)
        return '' if val is None else duration_string(val)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.DurationField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class EmailField(CharField):
    default_validators = [validators.validate_email]
    description = _("Email address")

    def __init__(self, *args, **kwargs):
        # max_length=254 to be compliant with RFCs 3696 and 5321
        kwargs['max_length'] = kwargs.get('max_length', 254)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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
        return super().formfield(**defaults)


class FilePathField(Field):
    description = _("File path")

    def __init__(self, verbose_name=None, name=None, path='', match=None,
                 recursive=False, allow_files=True, allow_folders=False, **kwargs):
        self.path, self.match, self.recursive = path, match, recursive
        self.allow_files, self.allow_folders = allow_files, allow_folders
        kwargs['max_length'] = kwargs.get('max_length', 100)
        super().__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_allowing_files_or_folders(**kwargs))
        return errors

    def _check_allowing_files_or_folders(self, **kwargs):
        if not self.allow_files and not self.allow_folders:
            return [
                checks.Error(
                    "FilePathFields must have either 'allow_files' or 'allow_folders' set to True.",
                    obj=self,
                    id='fields.E140',
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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
        if kwargs.get("max_length") == 100:
            del kwargs["max_length"]
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return str(value)

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
        return super().formfield(**defaults)

    def get_internal_type(self):
        return "FilePathField"


class FloatField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be a float."),
    }
    description = _("Floating point number")

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
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
        return super().formfield(**defaults)


class IntegerField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be an integer."),
    }
    description = _("Integer")

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_max_length_warning())
        return errors

    def _check_max_length_warning(self):
        if self.max_length is not None:
            return [
                checks.Warning(
                    "'max_length' is ignored when used with IntegerField",
                    hint="Remove 'max_length' from field",
                    obj=self,
                    id='fields.W122',
                )
            ]
        return []

    @cached_property
    def validators(self):
        # These validators can't be added at field initialization time since
        # they're based on values retrieved from `connection`.
        validators_ = super().validators
        internal_type = self.get_internal_type()
        min_value, max_value = connection.ops.integer_field_range(internal_type)
        if min_value is not None:
            for validator in validators_:
                if isinstance(validator, validators.MinValueValidator) and validator.limit_value >= min_value:
                    break
            else:
                validators_.append(validators.MinValueValidator(min_value))
        if max_value is not None:
            for validator in validators_:
                if isinstance(validator, validators.MaxValueValidator) and validator.limit_value <= max_value:
                    break
            else:
                validators_.append(validators.MaxValueValidator(max_value))
        return validators_

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return int(value)

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
        return super().formfield(**defaults)


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
        return super().formfield(**defaults)


class IPAddressField(Field):
    empty_strings_allowed = False
    description = _("IPv4 address")
    system_check_removed_details = {
        'msg': (
            'IPAddressField has been removed except for support in '
            'historical migrations.'
        ),
        'hint': 'Use GenericIPAddressField instead.',
        'id': 'fields.E900',
    }

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 15
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return str(value)

    def get_internal_type(self):
        return "IPAddressField"


class GenericIPAddressField(Field):
    empty_strings_allowed = False
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
        super().__init__(verbose_name, name, *args, **kwargs)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_blank_and_null_values(**kwargs))
        return errors

    def _check_blank_and_null_values(self, **kwargs):
        if not getattr(self, 'null', False) and getattr(self, 'blank', False):
            return [
                checks.Error(
                    'GenericIPAddressFields cannot have blank=True if null=False, '
                    'as blank values are stored as nulls.',
                    obj=self,
                    id='fields.E150',
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.unpack_ipv4 is not False:
            kwargs['unpack_ipv4'] = self.unpack_ipv4
        if self.protocol != "both":
            kwargs['protocol'] = self.protocol
        if kwargs.get("max_length") == 39:
            del kwargs['max_length']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "GenericIPAddressField"

    def to_python(self, value):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if ':' in value:
            return clean_ipv6_address(value, self.unpack_ipv4, self.error_messages['invalid'])
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops.adapt_ipaddressfield_value(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        if value and ':' in value:
            try:
                return clean_ipv6_address(value, self.unpack_ipv4)
            except exceptions.ValidationError:
                pass
        return str(value)

    def formfield(self, **kwargs):
        defaults = {
            'protocol': self.protocol,
            'form_class': forms.GenericIPAddressField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class NullBooleanField(Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be either None, True or False."),
    }
    description = _("Boolean (Either True, False or None)")

    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        kwargs['blank'] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return self.to_python(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.NullBooleanField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class PositiveIntegerRelDbTypeMixin:

    def rel_db_type(self, connection):
        """
        Return the data type that a related field pointing to this field should
        use. In most cases, a foreign key pointing to a positive integer
        primary key will have an integer column data type but some databases
        (e.g. MySQL) have an unsigned integer type. In that case
        (related_fields_match_type=True), the primary key should return its
        db_type.
        """
        if connection.features.related_fields_match_type:
            return self.db_type(connection)
        else:
            return IntegerField().db_type(connection=connection)


class PositiveIntegerField(PositiveIntegerRelDbTypeMixin, IntegerField):
    description = _("Positive integer")

    def get_internal_type(self):
        return "PositiveIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class PositiveSmallIntegerField(PositiveIntegerRelDbTypeMixin, IntegerField):
    description = _("Positive small integer")

    def get_internal_type(self):
        return "PositiveSmallIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class SlugField(CharField):
    default_validators = [validators.validate_slug]
    description = _("Slug (up to %(max_length)s)")

    def __init__(self, *args, max_length=50, db_index=True, allow_unicode=False, **kwargs):
        self.allow_unicode = allow_unicode
        if self.allow_unicode:
            self.default_validators = [validators.validate_unicode_slug]
        super().__init__(*args, max_length=max_length, db_index=db_index, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_length") == 50:
            del kwargs['max_length']
        if self.db_index is False:
            kwargs['db_index'] = False
        else:
            del kwargs['db_index']
        if self.allow_unicode is not False:
            kwargs['allow_unicode'] = self.allow_unicode
        return name, path, args, kwargs

    def get_internal_type(self):
        return "SlugField"

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.SlugField, 'allow_unicode': self.allow_unicode}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class SmallIntegerField(IntegerField):
    description = _("Small integer")

    def get_internal_type(self):
        return "SmallIntegerField"


class TextField(Field):
    description = _("Text")

    def get_internal_type(self):
        return "TextField"

    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return str(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.to_python(value)

    def formfield(self, **kwargs):
        # Passing max_length to forms.CharField means that the value's length
        # will be validated twice. This is considered acceptable since we want
        # the value in the form field (to pass into widget for example).
        defaults = {'max_length': self.max_length}
        if not self.choices:
            defaults['widget'] = forms.Textarea
        defaults.update(kwargs)
        return super().formfield(**defaults)


class TimeField(DateTimeCheckMixin, Field):
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
        super().__init__(verbose_name, name, **kwargs)

    def _check_fix_default_value(self):
        """
        Warn that using an actual date or datetime value is probably wrong;
        it's only evaluated on server startup.
        """
        if not self.has_default():
            return []

        now = timezone.now()
        if not timezone.is_naive(now):
            now = timezone.make_naive(now, timezone.utc)
        value = self.default
        if isinstance(value, datetime.datetime):
            second_offset = datetime.timedelta(seconds=10)
            lower = now - second_offset
            upper = now + second_offset
            if timezone.is_aware(value):
                value = timezone.make_naive(value, timezone.utc)
        elif isinstance(value, datetime.time):
            second_offset = datetime.timedelta(seconds=10)
            lower = now - second_offset
            upper = now + second_offset
            value = datetime.datetime.combine(now.date(), value)
            if timezone.is_aware(value):
                value = timezone.make_naive(value, timezone.utc).time()
        else:
            # No explicit time / datetime value -- no checks necessary
            return []
        if lower <= value <= upper:
            return [
                checks.Warning(
                    'Fixed default value provided.',
                    hint='It seems you set a fixed date / time / datetime '
                         'value as default for this field. This may not be '
                         'what you want. If you want to have the current date '
                         'as default, use `django.utils.timezone.now`',
                    obj=self,
                    id='fields.W161',
                )
            ]

        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
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
            return super().pre_save(model_instance, add)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.to_python(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        # Casts times into the format expected by the backend
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops.adapt_timefield_value(value)

    def value_to_string(self, obj):
        val = self.value_from_object(obj)
        return '' if val is None else val.isoformat()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.TimeField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class URLField(CharField):
    default_validators = [validators.URLValidator()]
    description = _("URL")

    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        super().__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_length") == 200:
            del kwargs['max_length']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause URL validation to be performed
        # twice.
        defaults = {
            'form_class': forms.URLField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class BinaryField(Field):
    description = _("Raw binary data")
    empty_values = [None, b'']

    def __init__(self, *args, **kwargs):
        kwargs['editable'] = False
        super().__init__(*args, **kwargs)
        if self.max_length is not None:
            self.validators.append(validators.MaxLengthValidator(self.max_length))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['editable']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "BinaryField"

    def get_placeholder(self, value, compiler, connection):
        return connection.ops.binary_placeholder_sql(value)

    def get_default(self):
        if self.has_default() and not callable(self.default):
            return self.default
        default = super().get_default()
        if default == '':
            return b''
        return default

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value is not None:
            return connection.Database.Binary(value)
        return value

    def value_to_string(self, obj):
        """Binary data is serialized as base64"""
        return b64encode(force_bytes(self.value_from_object(obj))).decode('ascii')

    def to_python(self, value):
        # If it's a string, it should be base64-encoded data
        if isinstance(value, str):
            return memoryview(b64decode(force_bytes(value)))
        return value


class UUIDField(Field):
    default_error_messages = {
        'invalid': _("'%(value)s' is not a valid UUID."),
    }
    description = 'Universally unique identifier'
    empty_strings_allowed = False

    def __init__(self, verbose_name=None, **kwargs):
        kwargs['max_length'] = 32
        super().__init__(verbose_name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    def get_internal_type(self):
        return "UUIDField"

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = self.to_python(value)

        if connection.features.has_native_uuid_field:
            return value
        return value.hex

    def to_python(self, value):
        if value is not None and not isinstance(value, uuid.UUID):
            try:
                return uuid.UUID(value)
            except (AttributeError, ValueError):
                raise exceptions.ValidationError(
                    self.error_messages['invalid'],
                    code='invalid',
                    params={'value': value},
                )
        return value

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.UUIDField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
