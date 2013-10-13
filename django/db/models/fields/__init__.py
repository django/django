from __future__ import unicode_literals

import copy
import datetime
import decimal
import math
import warnings
from base64 import b64decode, b64encode
from itertools import tee

from django.db import connection
from django.db.models.loading import get_model
from django.db.models.query_utils import QueryWrapper
from django.conf import settings
from django import forms
from django.core import exceptions, validators
from django.utils.datastructures import DictWrapper
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.functional import curry, total_ordering
from django.utils.itercompat import is_iterator
from django.utils.text import capfirst
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text, force_text, force_bytes
from django.utils.ipv6 import clean_ipv6_address
from django.utils import six

class Empty(object):
    pass

class NOT_PROVIDED:
    pass

# The values to use for "blank" in SelectFields. Will be appended to the start
# of most "choices" lists.
BLANK_CHOICE_DASH = [("", "---------")]

def _load_field(app_label, model_name, field_name):
    return get_model(app_label, model_name)._meta.get_field_by_name(field_name)[0]

class FieldDoesNotExist(Exception):
    pass

# A guide to Field parameters:
#
#   * name:      The name of the field specifed in the model.
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
class Field(object):
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
    default_validators = [] # Default set of validators
    default_error_messages = {
        'invalid_choice': _('Value %(value)r is not a valid choice.'),
        'null': _('This field cannot be null.'),
        'blank': _('This field cannot be blank.'),
        'unique': _('%(model_name)s with this %(field_label)s '
                    'already exists.'),
    }

    # Generic field type description, usually overriden by subclasses
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
        self.verbose_name = verbose_name
        self.primary_key = primary_key
        self.max_length, self._unique = max_length, unique
        self.blank, self.null = blank, null
        self.rel = rel
        self.default = default
        self.editable = editable
        self.serialize = serialize
        self.unique_for_date, self.unique_for_month = (unique_for_date,
                                                       unique_for_month)
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

        self.validators = self.default_validators + validators

        messages = {}
        for c in reversed(self.__class__.__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

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
        not a new copy of that field. So, we use the app cache to load the
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
            # Deferred model will not be found from the app cache. This could
            # be fixed by reconstructing the deferred model on unpickle.
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
        # backend-specific DATA_TYPES dictionary, looking up the field by its
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
            return (connection.creation.data_types[self.get_internal_type()]
                    % data)
        except KeyError:
            return None

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

        if lookup_type in (
                'iexact', 'contains', 'icontains',
                'startswith', 'istartswith', 'endswith', 'iendswith',
                'month', 'day', 'week_day', 'hour', 'minute', 'second',
                'isnull', 'search', 'regex', 'iregex',
            ):
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

        raise TypeError("Field has invalid lookup: %s" % lookup_type)

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
        first_choice = blank_choice if include_blank else []
        if self.choices:
            return first_choice + list(self.choices)
        rel_model = self.rel.to
        if hasattr(self.rel, 'get_related_field'):
            lst = [(getattr(x, self.rel.get_related_field().attname),
                        smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                       self.rel.limit_choices_to)]
        else:
            lst = [(x._get_pk_val(), smart_text(x))
                   for x in rel_model._default_manager.complex_filter(
                       self.rel.limit_choices_to)]
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
        if is_iterator(self._choices):
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
                flat.append((choice,value))
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

    def __repr__(self):
        """
        Displays the module, class and name of the field.
        """
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        name = getattr(self, 'name', None)
        if name is not None:
            return '<%s: %s>' % (path, name)
        return '<%s>' % path

class AutoField(Field):
    description = _("Integer")

    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be an integer."),
    }

    def __init__(self, *args, **kwargs):
        assert kwargs.get('primary_key', False) is True, \
               "%ss must have primary_key=True." % self.__class__.__name__
        kwargs['blank'] = True
        Field.__init__(self, *args, **kwargs)

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
        Field.__init__(self, *args, **kwargs)

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
        if value is None:
            return None
        return bool(value)

    def formfield(self, **kwargs):
        # Unlike most fields, BooleanField figures out include_blank from
        # self.null instead of self.blank.
        if self.choices:
            include_blank = (self.null or
                             not (self.has_default() or 'initial' in kwargs))
            defaults = {'choices': self.get_choices(
                                       include_blank=include_blank)}
        else:
            defaults = {'form_class': forms.BooleanField}
        defaults.update(kwargs)
        return super(BooleanField, self).formfield(**defaults)

class CharField(Field):
    description = _("String (up to %(max_length)s)")

    def __init__(self, *args, **kwargs):
        super(CharField, self).__init__(*args, **kwargs)
        self.validators.append(validators.MaxLengthValidator(self.max_length))

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        if isinstance(value, six.string_types) or value is None:
            return value
        return smart_text(value)

    def get_prep_value(self, value):
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
        Field.__init__(self, verbose_name, name, **kwargs)

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
        super(DateField,self).contribute_to_class(cls, name)
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
        value = self.to_python(value)
        if value is not None and settings.USE_TZ and timezone.is_naive(value):
            # For backwards compatibility, interpret naive datetimes in local
            # time. This won't work during DST change, but we can't do much
            # about it, so we let the exceptions percolate up the call stack.
            warnings.warn("DateTimeField %s.%s received a naive datetime (%s)"
                          " while time zone support is active." %
                          (self.model.__name__, self.name, value),
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
        Field.__init__(self, verbose_name, name, **kwargs)

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
        # Method moved to django.db.backends.util.
        #
        # It is preserved because it is used by the oracle backend
        # (django.db.backends.oracle.query), and also for
        # backwards-compatibility with any external code which may have used
        # this method.
        from django.db.backends import util
        return util.format_number(value, self.max_digits, self.decimal_places)

    def get_db_prep_save(self, value, connection):
        return connection.ops.value_to_db_decimal(self.to_python(value),
                self.max_digits, self.decimal_places)

    def get_prep_value(self, value):
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
        CharField.__init__(self, *args, **kwargs)

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
        self.allow_files, self.allow_folders =  allow_files, allow_folders
        kwargs['max_length'] = kwargs.get('max_length', 100)
        Field.__init__(self, verbose_name, name, **kwargs)

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

    def get_prep_value(self, value):
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
        kwargs['max_length'] = 15
        Field.__init__(self, *args, **kwargs)

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
        Field.__init__(self, verbose_name, name, *args, **kwargs)

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
        if value and ':' in value:
            try:
                return clean_ipv6_address(value, self.unpack_ipv4)
            except exceptions.ValidationError:
                pass
        return value

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
        Field.__init__(self, *args, **kwargs)

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
        if isinstance(value, six.string_types) or value is None:
            return value
        return smart_text(value)

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
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
        Field.__init__(self, verbose_name, name, **kwargs)

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
        CharField.__init__(self, verbose_name, name, **kwargs)

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
        value = super(BinaryField, self
            ).get_db_prep_value(value, connection, prepared)
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
