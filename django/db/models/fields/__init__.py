import copy
import datetime
import os
import re
import time
try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal    # for Python 2.3

from django.db import connection
from django.db.models import signals
from django.db.models.query_utils import QueryWrapper
from django.dispatch import dispatcher
from django.conf import settings
from django import forms
from django.core import exceptions
from django.utils.datastructures import DictWrapper
from django.utils.functional import curry
from django.utils.itercompat import tee
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy, ugettext as _
from django.utils.encoding import smart_unicode, force_unicode, smart_str
from django.utils import datetime_safe

class NOT_PROVIDED:
    pass

# The values to use for "blank" in SelectFields. Will be appended to the start of most "choices" lists.
BLANK_CHOICE_DASH = [("", "---------")]
BLANK_CHOICE_NONE = [("", "None")]

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

class Field(object):
    # Designates whether empty strings fundamentally are allowed at the
    # database level.
    empty_strings_allowed = True

    # These track each time a Field instance is created. Used to retain order.
    # The auto_creation_counter is used for fields that Django implicitly
    # creates, creation_counter is used for all user-specified fields.
    creation_counter = 0
    auto_creation_counter = -1

    def __init__(self, verbose_name=None, name=None, primary_key=False,
            max_length=None, unique=False, blank=False, null=False,
            db_index=False, rel=None, default=NOT_PROVIDED, editable=True,
            serialize=True, unique_for_date=None, unique_for_month=None,
            unique_for_year=None, choices=None, help_text='', db_column=None,
            db_tablespace=None, auto_created=False):
        self.name = name
        self.verbose_name = verbose_name
        self.primary_key = primary_key
        self.max_length, self._unique = max_length, unique
        self.blank, self.null = blank, null
        # Oracle treats the empty string ('') as null, so coerce the null
        # option whenever '' is a possible value.
        if self.empty_strings_allowed and connection.features.interprets_empty_strings_as_nulls:
            self.null = True
        self.rel = rel
        self.default = default
        self.editable = editable
        self.serialize = serialize
        self.unique_for_date, self.unique_for_month = unique_for_date, unique_for_month
        self.unique_for_year = unique_for_year
        self._choices = choices or []
        self.help_text = help_text
        self.db_column = db_column
        self.db_tablespace = db_tablespace or settings.DEFAULT_INDEX_TABLESPACE
        self.auto_created = auto_created

        # Set db_index to True if the field has a relationship and doesn't explicitly set db_index.
        self.db_index = db_index

        # Adjust the appropriate creation counter, and save our local copy.
        if auto_created:
            self.creation_counter = Field.auto_creation_counter
            Field.auto_creation_counter -= 1
        else:
            self.creation_counter = Field.creation_counter
            Field.creation_counter += 1

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        return cmp(self.creation_counter, other.creation_counter)

    def __deepcopy__(self, memodict):
        # We don't have to deepcopy very much here, since most things are not
        # intended to be altered after initial creation.
        obj = copy.copy(self)
        if self.rel:
            obj.rel = copy.copy(self.rel)
        memodict[id(self)] = obj
        return obj

    def to_python(self, value):
        """
        Converts the input value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """
        return value

    def db_type(self):
        """
        Returns the database column data type for this field, taking into
        account the DATABASE_ENGINE setting.
        """
        # The default implementation of this method looks at the
        # backend-specific DATA_TYPES dictionary, looking up the field by its
        # "internal type".
        #
        # A Field class can implement the get_internal_type() method to specify
        # which *preexisting* Django Field class it's most similar to -- i.e.,
        # an XMLField is represented by a TEXT column type, which is the same
        # as the TextField Django field type, which means XMLField's
        # get_internal_type() returns 'TextField'.
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

    def unique(self):
        return self._unique or self.primary_key
    unique = property(unique)

    def set_attributes_from_name(self, name):
        self.name = name
        self.attname, self.column = self.get_attname_column()
        if self.verbose_name is None and name:
            self.verbose_name = name.replace('_', ' ')

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)
        cls._meta.add_field(self)
        if self.choices:
            setattr(cls, 'get_%s_display' % self.name, curry(cls._get_FIELD_display, field=self))

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
        "Returns field's value just before saving."
        return getattr(model_instance, self.attname)

    def get_db_prep_value(self, value):
        """Returns field's value prepared for interacting with the database
        backend.

        Used by the default implementations of ``get_db_prep_save``and
        `get_db_prep_lookup```
        """
        return value

    def get_db_prep_save(self, value):
        "Returns field's value prepared for saving into a database."
        return self.get_db_prep_value(value)

    def get_db_prep_lookup(self, lookup_type, value):
        "Returns field's value prepared for database lookup."
        if hasattr(value, 'as_sql'):
            sql, params = value.as_sql()
            return QueryWrapper(('(%s)' % sql), params)
        if lookup_type in ('regex', 'iregex', 'month', 'day', 'search'):
            return [value]
        elif lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte'):
            return [self.get_db_prep_value(value)]
        elif lookup_type in ('range', 'in'):
            return [self.get_db_prep_value(v) for v in value]
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
            try:
                value = int(value)
            except ValueError:
                raise ValueError("The __year lookup type requires an integer argument")

            if self.get_internal_type() == 'DateField':
                return connection.ops.year_lookup_bounds_for_date_field(value)
            else:
                return connection.ops.year_lookup_bounds(value)

        raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def has_default(self):
        "Returns a boolean of whether this field has a default value."
        return self.default is not NOT_PROVIDED

    def get_default(self):
        "Returns the default value for this field."
        if self.has_default():
            if callable(self.default):
                return self.default()
            return force_unicode(self.default, strings_only=True)
        if not self.empty_strings_allowed or (self.null and not connection.features.interprets_empty_strings_as_nulls):
            return None
        return ""

    def get_validator_unique_lookup_type(self):
        return '%s__exact' % self.name

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        """Returns choices with a default blank choices included, for use
        as SelectField choices for this field."""
        first_choice = include_blank and blank_choice or []
        if self.choices:
            return first_choice + list(self.choices)
        rel_model = self.rel.to
        if hasattr(self.rel, 'get_related_field'):
            lst = [(getattr(x, self.rel.get_related_field().attname), smart_unicode(x)) for x in rel_model._default_manager.complex_filter(self.rel.limit_choices_to)]
        else:
            lst = [(x._get_pk_val(), smart_unicode(x)) for x in rel_model._default_manager.complex_filter(self.rel.limit_choices_to)]
        return first_choice + lst

    def get_choices_default(self):
        return self.get_choices()

    def get_flatchoices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        "Returns flattened choices with a default blank choice included."
        first_choice = include_blank and blank_choice or []
        return first_choice + list(self.flatchoices)

    def _get_val_from_obj(self, obj):
        if obj:
            return getattr(obj, self.attname)
        else:
            return self.get_default()

    def value_to_string(self, obj):
        """
        Returns a string value of this field from the passed obj.
        This is used by the serialization framework.
        """
        return smart_unicode(self._get_val_from_obj(obj))

    def bind(self, fieldmapping, original, bound_field_class):
        return bound_field_class(self, fieldmapping, original)

    def _get_choices(self):
        if hasattr(self._choices, 'next'):
            choices, self._choices = tee(self._choices)
            return choices
        else:
            return self._choices
    choices = property(_get_choices)

    def _get_flatchoices(self):
        """Flattened version of choices tuple."""
        flat = []
        for choice, value in self.choices:
            if type(value) in (list, tuple):
                flat.extend(value)
            else:
                flat.append((choice,value))
        return flat
    flatchoices = property(_get_flatchoices)

    def save_form_data(self, instance, data):
        setattr(instance, self.name, data)

    def formfield(self, form_class=forms.CharField, **kwargs):
        "Returns a django.forms.Field instance for this database Field."
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        if self.has_default():
            defaults['initial'] = self.get_default()
            if callable(self.default):
                defaults['show_hidden_initial'] = True
        if self.choices:
            # Fields with choices get special treatment. 
            include_blank = self.blank or not (self.has_default() or 'initial' in kwargs)
            defaults['choices'] = self.get_choices(include_blank=include_blank)
            defaults['coerce'] = self.to_python
            if self.null:
                defaults['empty_value'] = None
            form_class = forms.TypedChoiceField
            # Many of the subclass-specific formfield arguments (min_value,
            # max_value) don't apply for choice fields, so be sure to only pass
            # the values that TypedChoiceField will understand.
            for k in kwargs.keys():
                if k not in ('coerce', 'empty_value', 'choices', 'required',
                             'widget', 'label', 'initial', 'help_text',
                             'error_messages'):
                    del kwargs[k]
        defaults.update(kwargs)
        return form_class(**defaults)

    def value_from_object(self, obj):
        "Returns the value of this field in the given model instance."
        return getattr(obj, self.attname)

class AutoField(Field):
    empty_strings_allowed = False
    def __init__(self, *args, **kwargs):
        assert kwargs.get('primary_key', False) is True, "%ss must have primary_key=True." % self.__class__.__name__
        kwargs['blank'] = True
        Field.__init__(self, *args, **kwargs)

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                _("This value must be an integer."))

    def get_db_prep_value(self, value):
        if value is None:
            return None
        return int(value)

    def contribute_to_class(self, cls, name):
        assert not cls._meta.has_auto_field, "A model can't have more than one AutoField."
        super(AutoField, self).contribute_to_class(cls, name)
        cls._meta.has_auto_field = True
        cls._meta.auto_field = self

    def formfield(self, **kwargs):
        return None

class BooleanField(Field):
    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        if 'default' not in kwargs and not kwargs.get('null'):
            kwargs['default'] = False
        Field.__init__(self, *args, **kwargs)

    def get_internal_type(self):
        return "BooleanField"

    def to_python(self, value):
        if value in (True, False): return value
        if value in ('t', 'True', '1'): return True
        if value in ('f', 'False', '0'): return False
        raise exceptions.ValidationError(
            _("This value must be either True or False."))

    def get_db_prep_lookup(self, lookup_type, value):
        # Special-case handling for filters coming from a web request (e.g. the
        # admin interface). Only works for scalar values (not lists). If you're
        # passing in a list, you might as well make things the right type when
        # constructing the list.
        if value in ('1', '0'):
            value = bool(int(value))
        return super(BooleanField, self).get_db_prep_lookup(lookup_type, value)

    def get_db_prep_value(self, value):
        if value is None:
            return None
        return bool(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.BooleanField}
        defaults.update(kwargs)
        return super(BooleanField, self).formfield(**defaults)

class CharField(Field):
    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        if isinstance(value, basestring):
            return value
        if value is None:
            if self.null:
                return value
            else:
                raise exceptions.ValidationError(
                    ugettext_lazy("This field cannot be null."))
        return smart_unicode(value)

    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(CharField, self).formfield(**defaults)

# TODO: Maybe move this into contrib, because it's specialized.
class CommaSeparatedIntegerField(CharField):
    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.RegexField,
            'regex': '^[\d,]+$',
            'max_length': self.max_length,
            'error_messages': {
                'invalid': _(u'Enter only digits separated by commas.'),
            }
        }
        defaults.update(kwargs)
        return super(CommaSeparatedIntegerField, self).formfield(**defaults)

ansi_date_re = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')

class DateField(Field):
    empty_strings_allowed = False
    def __init__(self, verbose_name=None, name=None, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        #HACKs : auto_now_add/auto_now should be done as a default or a pre_save.
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
            return value.date()
        if isinstance(value, datetime.date):
            return value

        if not ansi_date_re.search(value):
            raise exceptions.ValidationError(
                _('Enter a valid date in YYYY-MM-DD format.'))
        # Now that we have the date string in YYYY-MM-DD format, check to make
        # sure it's a valid date.
        # We could use time.strptime here and catch errors, but datetime.date
        # produces much friendlier error messages.
        year, month, day = map(int, value.split('-'))
        try:
            return datetime.date(year, month, day)
        except ValueError, e:
            msg = _('Invalid date: %s') % _(str(e))
            raise exceptions.ValidationError(msg)

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = datetime.datetime.now()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(DateField, self).pre_save(model_instance, add)

    def contribute_to_class(self, cls, name):
        super(DateField,self).contribute_to_class(cls, name)
        if not self.null:
            setattr(cls, 'get_next_by_%s' % self.name,
                curry(cls._get_next_or_previous_by_FIELD, field=self, is_next=True))
            setattr(cls, 'get_previous_by_%s' % self.name,
                curry(cls._get_next_or_previous_by_FIELD, field=self, is_next=False))

    def get_db_prep_lookup(self, lookup_type, value):
        # For "__month" and "__day" lookups, convert the value to a string so
        # the database backend always sees a consistent type.
        if lookup_type in ('month', 'day'):
            return [force_unicode(value)]
        return super(DateField, self).get_db_prep_lookup(lookup_type, value)

    def get_db_prep_value(self, value):
        # Casts dates into the format expected by the backend
        return connection.ops.value_to_db_date(self.to_python(value))

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            data = ''
        else:
            data = datetime_safe.new_date(val).strftime("%Y-%m-%d")
        return data

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateField}
        defaults.update(kwargs)
        return super(DateField, self).formfield(**defaults)

class DateTimeField(DateField):
    def get_internal_type(self):
        return "DateTimeField"

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)

        # Attempt to parse a datetime:
        value = smart_str(value)
        # split usecs, because they are not recognized by strptime.
        if '.' in value:
            try:
                value, usecs = value.split('.')
                usecs = int(usecs)
            except ValueError:
                raise exceptions.ValidationError(
                    _('Enter a valid date/time in YYYY-MM-DD HH:MM[:ss[.uuuuuu]] format.'))
        else:
            usecs = 0
        kwargs = {'microsecond': usecs}
        try: # Seconds are optional, so try converting seconds first.
            return datetime.datetime(*time.strptime(value, '%Y-%m-%d %H:%M:%S')[:6],
                                     **kwargs)

        except ValueError:
            try: # Try without seconds.
                return datetime.datetime(*time.strptime(value, '%Y-%m-%d %H:%M')[:5],
                                         **kwargs)
            except ValueError: # Try without hour/minutes/seconds.
                try:
                    return datetime.datetime(*time.strptime(value, '%Y-%m-%d')[:3],
                                             **kwargs)
                except ValueError:
                    raise exceptions.ValidationError(
                        _('Enter a valid date/time in YYYY-MM-DD HH:MM[:ss[.uuuuuu]] format.'))

    def get_db_prep_value(self, value):
        # Casts dates into the format expected by the backend
        return connection.ops.value_to_db_datetime(self.to_python(value))

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            data = ''
        else:
            d = datetime_safe.new_datetime(val)
            data = d.strftime('%Y-%m-%d %H:%M:%S')
        return data

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateTimeField}
        defaults.update(kwargs)
        return super(DateTimeField, self).formfield(**defaults)

class DecimalField(Field):
    empty_strings_allowed = False
    def __init__(self, verbose_name=None, name=None, max_digits=None, decimal_places=None, **kwargs):
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
                _("This value must be a decimal number."))

    def _format(self, value):
        if isinstance(value, basestring) or value is None:
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

    def get_db_prep_value(self, value):
        return connection.ops.value_to_db_decimal(self.to_python(value),
                self.max_digits, self.decimal_places)

    def formfield(self, **kwargs):
        defaults = {
            'max_digits': self.max_digits,
            'decimal_places': self.decimal_places,
            'form_class': forms.DecimalField,
        }
        defaults.update(kwargs)
        return super(DecimalField, self).formfield(**defaults)

class EmailField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 75)
        CharField.__init__(self, *args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.EmailField}
        defaults.update(kwargs)
        return super(EmailField, self).formfield(**defaults)

class FilePathField(Field):
    def __init__(self, verbose_name=None, name=None, path='', match=None, recursive=False, **kwargs):
        self.path, self.match, self.recursive = path, match, recursive
        kwargs['max_length'] = kwargs.get('max_length', 100)
        Field.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'path': self.path,
            'match': self.match,
            'recursive': self.recursive,
            'form_class': forms.FilePathField,
        }
        defaults.update(kwargs)
        return super(FilePathField, self).formfield(**defaults)

    def get_internal_type(self):
        return "FilePathField"

class FloatField(Field):
    empty_strings_allowed = False

    def get_db_prep_value(self, value):
        if value is None:
            return None
        return float(value)

    def get_internal_type(self):
        return "FloatField"

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.FloatField}
        defaults.update(kwargs)
        return super(FloatField, self).formfield(**defaults)

class IntegerField(Field):
    empty_strings_allowed = False
    def get_db_prep_value(self, value):
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
                _("This value must be an integer."))

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IntegerField}
        defaults.update(kwargs)
        return super(IntegerField, self).formfield(**defaults)

class IPAddressField(Field):
    empty_strings_allowed = False
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 15
        Field.__init__(self, *args, **kwargs)

    def get_internal_type(self):
        return "IPAddressField"

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IPAddressField}
        defaults.update(kwargs)
        return super(IPAddressField, self).formfield(**defaults)

class NullBooleanField(Field):
    empty_strings_allowed = False
    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        Field.__init__(self, *args, **kwargs)

    def get_internal_type(self):
        return "NullBooleanField"

    def to_python(self, value):
        if value in (None, True, False): return value
        if value in ('None',): return None
        if value in ('t', 'True', '1'): return True
        if value in ('f', 'False', '0'): return False
        raise exceptions.ValidationError(
            _("This value must be either None, True or False."))

    def get_db_prep_lookup(self, lookup_type, value):
        # Special-case handling for filters coming from a web request (e.g. the
        # admin interface). Only works for scalar values (not lists). If you're
        # passing in a list, you might as well make things the right type when
        # constructing the list.
        if value in ('1', '0'):
            value = bool(int(value))
        return super(NullBooleanField, self).get_db_prep_lookup(lookup_type, value)

    def get_db_prep_value(self, value):
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

class PhoneNumberField(Field):
    def get_internal_type(self):
        return "PhoneNumberField"

    def formfield(self, **kwargs):
        from django.contrib.localflavor.us.forms import USPhoneNumberField
        defaults = {'form_class': USPhoneNumberField}
        defaults.update(kwargs)
        return super(PhoneNumberField, self).formfield(**defaults)

class PositiveIntegerField(IntegerField):
    def get_internal_type(self):
        return "PositiveIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0}
        defaults.update(kwargs)
        return super(PositiveIntegerField, self).formfield(**defaults)

class PositiveSmallIntegerField(IntegerField):
    def get_internal_type(self):
        return "PositiveSmallIntegerField"

    def formfield(self, **kwargs):
        defaults = {'min_value': 0}
        defaults.update(kwargs)
        return super(PositiveSmallIntegerField, self).formfield(**defaults)

class SlugField(CharField):
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
    def get_internal_type(self):
        return "SmallIntegerField"

class TextField(Field):
    def get_internal_type(self):
        return "TextField"

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(TextField, self).formfield(**defaults)

class TimeField(Field):
    empty_strings_allowed = False
    def __init__(self, verbose_name=None, name=None, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
        Field.__init__(self, verbose_name, name, **kwargs)

    def get_internal_type(self):
        return "TimeField"

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value

        # Attempt to parse a datetime:
        value = smart_str(value)
        # split usecs, because they are not recognized by strptime.
        if '.' in value:
            try:
                value, usecs = value.split('.')
                usecs = int(usecs)
            except ValueError:
                raise exceptions.ValidationError(
                    _('Enter a valid time in HH:MM[:ss[.uuuuuu]] format.'))
        else:
            usecs = 0
        kwargs = {'microsecond': usecs}

        try: # Seconds are optional, so try converting seconds first.
            return datetime.time(*time.strptime(value, '%H:%M:%S')[3:6],
                                 **kwargs)
        except ValueError:
            try: # Try without seconds.
                return datetime.time(*time.strptime(value, '%H:%M')[3:5],
                                         **kwargs)
            except ValueError:
                raise exceptions.ValidationError(
                    _('Enter a valid time in HH:MM[:ss[.uuuuuu]] format.'))

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = datetime.datetime.now().time()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(TimeField, self).pre_save(model_instance, add)

    def get_db_prep_value(self, value):
        # Casts times into the format expected by the backend
        return connection.ops.value_to_db_time(self.to_python(value))

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            data = ''
        else:
            data = val.strftime("%H:%M:%S")
        return data

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.TimeField}
        defaults.update(kwargs)
        return super(TimeField, self).formfield(**defaults)

class URLField(CharField):
    def __init__(self, verbose_name=None, name=None, verify_exists=True, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        self.verify_exists = verify_exists
        CharField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.URLField, 'verify_exists': self.verify_exists}
        defaults.update(kwargs)
        return super(URLField, self).formfield(**defaults)

class USStateField(Field):
    def get_internal_type(self):
        return "USStateField"

    def formfield(self, **kwargs):
        from django.contrib.localflavor.us.forms import USStateSelect
        defaults = {'widget': USStateSelect}
        defaults.update(kwargs)
        return super(USStateField, self).formfield(**defaults)

class XMLField(TextField):
    def __init__(self, verbose_name=None, name=None, schema_path=None, **kwargs):
        self.schema_path = schema_path
        Field.__init__(self, verbose_name, name, **kwargs)
