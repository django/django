from django.db.models import signals
from django.dispatch import dispatcher
from django.conf import settings
from django.core import validators
from django import oldforms
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import curry
from django.utils.itercompat import tee
from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy
import datetime, os, time

class NOT_PROVIDED:
    pass

# Values for filter_interface.
HORIZONTAL, VERTICAL = 1, 2

# The values to use for "blank" in SelectFields. Will be appended to the start of most "choices" lists.
BLANK_CHOICE_DASH = [("", "---------")]
BLANK_CHOICE_NONE = [("", "None")]

# prepares a value for use in a LIKE query
prep_for_like_query = lambda x: str(x).replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")

# returns the <ul> class for a given radio_admin value
get_ul_class = lambda x: 'radiolist%s' % ((x == HORIZONTAL) and ' inline' or '')

class FieldDoesNotExist(Exception):
    pass

def manipulator_validator_unique(f, opts, self, field_data, all_data):
    "Validates that the value is unique for this field."
    lookup_type = f.get_validator_unique_lookup_type()
    try:
        old_obj = self.manager.get(**{lookup_type: field_data})
    except ObjectDoesNotExist:
        return
    if getattr(self, 'original_object', None) and self.original_object._get_pk_val() == old_obj._get_pk_val():
        return
    raise validators.ValidationError, gettext("%(optname)s with this %(fieldname)s already exists.") % {'optname': capfirst(opts.verbose_name), 'fieldname': f.verbose_name}

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

    # Tracks each time a Field instance is created. Used to retain order.
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None, primary_key=False,
        maxlength=None, unique=False, blank=False, null=False, db_index=False,
        core=False, rel=None, default=NOT_PROVIDED, editable=True,
        prepopulate_from=None, unique_for_date=None, unique_for_month=None,
        unique_for_year=None, validator_list=None, choices=None, radio_admin=None,
        help_text='', db_column=None):
        self.name = name
        self.verbose_name = verbose_name
        self.primary_key = primary_key
        self.maxlength, self.unique = maxlength, unique
        self.blank, self.null = blank, null
        self.core, self.rel, self.default = core, rel, default
        self.editable = editable
        self.validator_list = validator_list or []
        self.prepopulate_from = prepopulate_from
        self.unique_for_date, self.unique_for_month = unique_for_date, unique_for_month
        self.unique_for_year = unique_for_year
        self._choices = choices or []
        self.radio_admin = radio_admin
        self.help_text = help_text
        self.db_column = db_column

        # Set db_index to True if the field has a relationship and doesn't explicitly set db_index.
        self.db_index = db_index

        # Increase the creation counter, and save our local copy.
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        return cmp(self.creation_counter, other.creation_counter)

    def to_python(self, value):
        """
        Converts the input value into the expected Python data type, raising
        validators.ValidationError if the data can't be converted. Returns the
        converted value. Subclasses should override this.
        """
        return value

    def validate_full(self, field_data, all_data):
        """
        Returns a list of errors for this field. This is the main interface,
        as it encapsulates some basic validation logic used by all fields.
        Subclasses should implement validate(), not validate_full().
        """
        if not self.blank and not field_data:
            return [gettext_lazy('This field is required.')]
        try:
            self.validate(field_data, all_data)
        except validators.ValidationError, e:
            return e.messages
        return []

    def validate(self, field_data, all_data):
        """
        Raises validators.ValidationError if field_data has any errors.
        Subclasses should override this to specify field-specific validation
        logic. This method should assume field_data has already been converted
        into the appropriate data type by Field.to_python().
        """
        pass

    def set_attributes_from_name(self, name):
        self.name = name
        self.attname, self.column = self.get_attname_column()
        self.verbose_name = self.verbose_name or (name and name.replace('_', ' '))

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

    def get_db_prep_save(self, value):
        "Returns field's value prepared for saving into a database."
        # Oracle treats empty strings ('') the same as NULLs.
        # To get around this wart, we need to change it to something else...
        if settings.DATABASE_ENGINE == 'oracle' and value == '':
            value = ' '
        return value

    def get_db_prep_lookup(self, lookup_type, value):
        "Returns field's value prepared for database lookup."
        if lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte', 'year', 'month', 'day', 'search'):
            return [value]
        elif lookup_type in ('range', 'in'):
            return value
        elif lookup_type in ('contains', 'icontains'):
            return ["%%%s%%" % prep_for_like_query(value)]
        elif lookup_type == 'iexact':
            return [prep_for_like_query(value)]
        elif lookup_type in ('startswith', 'istartswith'):
            return ["%s%%" % prep_for_like_query(value)]
        elif lookup_type in ('endswith', 'iendswith'):
            return ["%%%s" % prep_for_like_query(value)]
        elif lookup_type == 'isnull':
            return []
        raise TypeError, "Field has invalid lookup: %s" % lookup_type

    def has_default(self):
        "Returns a boolean of whether this field has a default value."
        return self.default is not NOT_PROVIDED

    def get_default(self):
        "Returns the default value for this field."
        if self.default is not NOT_PROVIDED:
            if callable(self.default):
                return self.default()
            return self.default
        if not self.empty_strings_allowed or self.null:
            return None
        return ""

    def get_manipulator_field_names(self, name_prefix):
        """
        Returns a list of field names that this object adds to the manipulator.
        """
        return [name_prefix + self.name]

    def prepare_field_objs_and_params(self, manipulator, name_prefix):
        params = {'validator_list': self.validator_list[:]}
        if self.maxlength and not self.choices: # Don't give SelectFields a maxlength parameter.
            params['maxlength'] = self.maxlength

        if self.choices:
            if self.radio_admin:
                field_objs = [oldforms.RadioSelectField]
                params['ul_class'] = get_ul_class(self.radio_admin)
            else:
                field_objs = [oldforms.SelectField]

            params['choices'] = self.get_choices_default()
        else:
            field_objs = self.get_manipulator_field_objs()
        return (field_objs, params)

    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False, follow=True):
        """
        Returns a list of oldforms.FormField instances for this field. It
        calculates the choices at runtime, not at compile time.

        name_prefix is a prefix to prepend to the "field_name" argument.
        rel is a boolean specifying whether this field is in a related context.
        """
        field_objs, params = self.prepare_field_objs_and_params(manipulator, name_prefix)

        # Add the "unique" validator(s).
        for field_name_list in opts.unique_together:
            if field_name_list[0] == self.name:
                params['validator_list'].append(getattr(manipulator, 'isUnique%s' % '_'.join(field_name_list)))

        # Add the "unique for..." validator(s).
        if self.unique_for_date:
            params['validator_list'].append(getattr(manipulator, 'isUnique%sFor%s' % (self.name, self.unique_for_date)))
        if self.unique_for_month:
            params['validator_list'].append(getattr(manipulator, 'isUnique%sFor%s' % (self.name, self.unique_for_month)))
        if self.unique_for_year:
            params['validator_list'].append(getattr(manipulator, 'isUnique%sFor%s' % (self.name, self.unique_for_year)))
        if self.unique or (self.primary_key and not rel):
            params['validator_list'].append(curry(manipulator_validator_unique, self, opts, manipulator))

        # Only add is_required=True if the field cannot be blank. Primary keys
        # are a special case, and fields in a related context should set this
        # as False, because they'll be caught by a separate validator --
        # RequiredIfOtherFieldGiven.
        params['is_required'] = not self.blank and not self.primary_key and not rel

        # BooleanFields (CheckboxFields) are a special case. They don't take
        # is_required.
        if isinstance(self, BooleanField):
            del params['is_required']

        # If this field is in a related context, check whether any other fields
        # in the related object have core=True. If so, add a validator --
        # RequiredIfOtherFieldsGiven -- to this FormField.
        if rel and not self.blank and not isinstance(self, AutoField) and not isinstance(self, FileField):
            # First, get the core fields, if any.
            core_field_names = []
            for f in opts.fields:
                if f.core and f != self:
                    core_field_names.extend(f.get_manipulator_field_names(name_prefix))
            # Now, if there are any, add the validator to this FormField.
            if core_field_names:
                params['validator_list'].append(validators.RequiredIfOtherFieldsGiven(core_field_names, gettext_lazy("This field is required.")))

        # Finally, add the field_names.
        field_names = self.get_manipulator_field_names(name_prefix)
        return [man(field_name=field_names[i], **params) for i, man in enumerate(field_objs)]

    def get_validator_unique_lookup_type(self):
        return '%s__exact' % self.name

    def get_manipulator_new_data(self, new_data, rel=False):
        """
        Given the full new_data dictionary (from the manipulator), returns this
        field's data.
        """
        if rel:
            return new_data.get(self.name, [self.get_default()])[0]
        val = new_data.get(self.name, self.get_default())
        if not self.empty_strings_allowed and val == '' and self.null:
            val = None
        return val

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        "Returns a list of tuples used as SelectField choices for this field."
        first_choice = include_blank and blank_choice or []
        if self.choices:
            return first_choice + list(self.choices)
        rel_model = self.rel.to
        if hasattr(self.rel, 'get_related_field'):
            lst = [(getattr(x, self.rel.get_related_field().attname), str(x)) for x in rel_model._default_manager.complex_filter(self.rel.limit_choices_to)]
        else:
            lst = [(x._get_pk_val(), str(x)) for x in rel_model._default_manager.complex_filter(self.rel.limit_choices_to)]
        return first_choice + lst

    def get_choices_default(self):
        if self.radio_admin:
            return self.get_choices(include_blank=self.blank, blank_choice=BLANK_CHOICE_NONE)
        else:
            return self.get_choices()

    def _get_val_from_obj(self, obj):
        if obj:
            return getattr(obj, self.attname)
        else:
            return self.get_default()

    def flatten_data(self, follow, obj=None):
        """
        Returns a dictionary mapping the field's manipulator field names to its
        "flattened" string values for the admin view. obj is the instance to
        extract the values from.
        """
        return {self.attname: self._get_val_from_obj(obj)}

    def get_follow(self, override=None):
        if override != None:
            return override
        else:
            return self.editable

    def bind(self, fieldmapping, original, bound_field_class):
        return bound_field_class(self, fieldmapping, original)

    def _get_choices(self):
        if hasattr(self._choices, 'next'):
            choices, self._choices = tee(self._choices)
            return choices
        else:
            return self._choices
    choices = property(_get_choices)

    def formfield(self, **kwargs):
        "Returns a django.newforms.Field instance for this database Field."
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.CharField(**defaults)

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
            raise validators.ValidationError, gettext("This value must be an integer.")

    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False, follow=True):
        if not rel:
            return [] # Don't add a FormField unless it's in a related context.
        return Field.get_manipulator_fields(self, opts, manipulator, change, name_prefix, rel, follow)

    def get_manipulator_field_objs(self):
        return [oldforms.HiddenField]

    def get_manipulator_new_data(self, new_data, rel=False):
        # Never going to be called
        # Not in main change pages
        # ignored in related context
        if not rel:
            return None
        return Field.get_manipulator_new_data(self, new_data, rel)

    def contribute_to_class(self, cls, name):
        assert not cls._meta.has_auto_field, "A model can't have more than one AutoField."
        super(AutoField, self).contribute_to_class(cls, name)
        cls._meta.has_auto_field = True

    def formfield(self, **kwargs):
        return None

class BooleanField(Field):
    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        Field.__init__(self, *args, **kwargs)

    def to_python(self, value):
        if value in (True, False): return value
        if value in ('t', 'True', '1'): return True
        if value in ('f', 'False', '0'): return False
        raise validators.ValidationError, gettext("This value must be either True or False.")

    def get_manipulator_field_objs(self):
        return [oldforms.CheckboxField]

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.BooleanField(**defaults)

class CharField(Field):
    def get_manipulator_field_objs(self):
        return [oldforms.TextField]

    def to_python(self, value):
        if isinstance(value, basestring):
            return value
        if value is None:
            if self.null:
                return value
            else:
                raise validators.ValidationError, gettext_lazy("This field cannot be null.")
        return str(value)

    def formfield(self, **kwargs):
        defaults = {'max_length': self.maxlength, 'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.CharField(**defaults)

# TODO: Maybe move this into contrib, because it's specialized.
class CommaSeparatedIntegerField(CharField):
    def get_manipulator_field_objs(self):
        return [oldforms.CommaSeparatedIntegerField]

class DateField(Field):
    empty_strings_allowed = False
    def __init__(self, verbose_name=None, name=None, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        #HACKs : auto_now_add/auto_now should be done as a default or a pre_save.
        if auto_now or auto_now_add:
            kwargs['editable'] = False
            kwargs['blank'] = True
        Field.__init__(self, verbose_name, name, **kwargs)

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        validators.isValidANSIDate(value, None)
        try:
            return datetime.date(*time.strptime(value, '%Y-%m-%d')[:3])
        except ValueError:
            raise validators.ValidationError, gettext('Enter a valid date in YYYY-MM-DD format.')

    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type == 'range':
            value = [str(v) for v in value]
        elif lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte') and hasattr(value, 'strftime'):
            value = value.strftime('%Y-%m-%d')
        else:
            value = str(value)
        return Field.get_db_prep_lookup(self, lookup_type, value)

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

    # Needed because of horrible auto_now[_add] behaviour wrt. editable
    def get_follow(self, override=None):
        if override != None:
            return override
        else:
            return self.editable or self.auto_now or self.auto_now_add

    def get_db_prep_save(self, value):
        # Casts dates into string format for entry into database.
        if isinstance(value, datetime.datetime):
            if settings.DATABASE_ENGINE != 'oracle':
                # Oracle does not need a string conversion
                value = value.date().strftime('%Y-%m-%d')
        elif isinstance(value, datetime.date):
            if settings.DATABASE_ENGINE != 'oracle':
                # Oracle does not need a string conversion
                value = value.strftime('%Y-%m-%d')
        return Field.get_db_prep_save(self, value)

    def get_manipulator_field_objs(self):
        return [oldforms.DateField]

    def flatten_data(self, follow, obj=None):
        val = self._get_val_from_obj(obj)
        return {self.attname: (val is not None and val.strftime("%Y-%m-%d") or '')}

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.DateField(**defaults)

class DateTimeField(DateField):
    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        try: # Seconds are optional, so try converting seconds first.
            return datetime.datetime(*time.strptime(value, '%Y-%m-%d %H:%M:%S')[:6])
        except ValueError:
            try: # Try without seconds.
                return datetime.datetime(*time.strptime(value, '%Y-%m-%d %H:%M')[:5])
            except ValueError: # Try without hour/minutes/seconds.
                try:
                    return datetime.datetime(*time.strptime(value, '%Y-%m-%d')[:3])
                except ValueError:
                    raise validators.ValidationError, gettext('Enter a valid date/time in YYYY-MM-DD HH:MM format.')

    def get_db_prep_save(self, value):
        # Casts dates into string format for entry into database.
        if value is not None:
            # MySQL/Oracle will throw a warning if microseconds are given, because
            # neither database supports microseconds.
            if settings.DATABASE_ENGINE in ('mysql', 'oracle') and hasattr(value, 'microsecond'):
                value = value.replace(microsecond=0)
            # cx_Oracle wants the raw datetime instead of a string.
            if settings.DATABASE_ENGINE != 'oracle':
                value = str(value)
        return Field.get_db_prep_save(self, value)

    def get_db_prep_lookup(self, lookup_type, value):
        # Oracle will throw an error if microseconds are given, because it
        # doesn't support microseconds.
        if settings.DATABASE_ENGINE == 'oracle' and hasattr(value, 'microsecond'):
            value = value.replace(microsecond=0)
        if lookup_type == 'range':
            value = [str(v) for v in value]
        else:
            value = str(value)
        return Field.get_db_prep_lookup(self, lookup_type, value)

    def get_manipulator_field_objs(self):
        return [oldforms.DateField, oldforms.TimeField]

    def get_manipulator_field_names(self, name_prefix):
        return [name_prefix + self.name + '_date', name_prefix + self.name + '_time']

    def get_manipulator_new_data(self, new_data, rel=False):
        date_field, time_field = self.get_manipulator_field_names('')
        if rel:
            d = new_data.get(date_field, [None])[0]
            t = new_data.get(time_field, [None])[0]
        else:
            d = new_data.get(date_field, None)
            t = new_data.get(time_field, None)
        if d is not None and t is not None:
            return datetime.datetime.combine(d, t)
        return self.get_default()

    def flatten_data(self,follow, obj = None):
        val = self._get_val_from_obj(obj)
        date_field, time_field = self.get_manipulator_field_names('')
        # cx_Oracle does not support strftime
        if settings.DATABASE_ENGINE == 'oracle':
            return {date_field: (val is not None or ''),
                    time_field: (val is not None or '')}
        else:
            return {date_field: (val is not None and val.strftime("%Y-%m-%d") or ''),
                    time_field: (val is not None and val.strftime("%H:%M:%S") or '')}

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.DateTimeField(**defaults)

class EmailField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs['maxlength'] = 75
        CharField.__init__(self, *args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def get_manipulator_field_objs(self):
        return [oldforms.EmailField]

    def validate(self, field_data, all_data):
        validators.isValidEmail(field_data, all_data)

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.EmailField(**defaults)

class FileField(Field):
    def __init__(self, verbose_name=None, name=None, upload_to='', **kwargs):
        self.upload_to = upload_to
        Field.__init__(self, verbose_name, name, **kwargs)

    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False, follow=True):
        field_list = Field.get_manipulator_fields(self, opts, manipulator, change, name_prefix, rel, follow)
        if not self.blank:
            if rel:
                # This validator makes sure FileFields work in a related context.
                class RequiredFileField(object):
                    def __init__(self, other_field_names, other_file_field_name):
                        self.other_field_names = other_field_names
                        self.other_file_field_name = other_file_field_name
                        self.always_test = True
                    def __call__(self, field_data, all_data):
                        if not all_data.get(self.other_file_field_name, False):
                            c = validators.RequiredIfOtherFieldsGiven(self.other_field_names, gettext_lazy("This field is required."))
                            c(field_data, all_data)
                # First, get the core fields, if any.
                core_field_names = []
                for f in opts.fields:
                    if f.core and f != self:
                        core_field_names.extend(f.get_manipulator_field_names(name_prefix))
                # Now, if there are any, add the validator to this FormField.
                if core_field_names:
                    field_list[0].validator_list.append(RequiredFileField(core_field_names, field_list[1].field_name))
            else:
                v = validators.RequiredIfOtherFieldNotGiven(field_list[1].field_name, gettext_lazy("This field is required."))
                v.always_test = True
                field_list[0].validator_list.append(v)
                field_list[0].is_required = field_list[1].is_required = False

        # If the raw path is passed in, validate it's under the MEDIA_ROOT.
        def isWithinMediaRoot(field_data, all_data):
            f = os.path.abspath(os.path.join(settings.MEDIA_ROOT, field_data))
            if not f.startswith(os.path.abspath(os.path.normpath(settings.MEDIA_ROOT))):
                raise validators.ValidationError, _("Enter a valid filename.")
        field_list[1].validator_list.append(isWithinMediaRoot)
        return field_list

    def contribute_to_class(self, cls, name):
        super(FileField, self).contribute_to_class(cls, name)
        setattr(cls, 'get_%s_filename' % self.name, curry(cls._get_FIELD_filename, field=self))
        setattr(cls, 'get_%s_url' % self.name, curry(cls._get_FIELD_url, field=self))
        setattr(cls, 'get_%s_size' % self.name, curry(cls._get_FIELD_size, field=self))
        setattr(cls, 'save_%s_file' % self.name, lambda instance, filename, raw_contents: instance._save_FIELD_file(self, filename, raw_contents))
        dispatcher.connect(self.delete_file, signal=signals.post_delete, sender=cls)

    def delete_file(self, instance):
        if getattr(instance, self.attname):
            file_name = getattr(instance, 'get_%s_filename' % self.name)()
            # If the file exists and no other object of this type references it,
            # delete it from the filesystem.
            if os.path.exists(file_name) and \
                not instance.__class__._default_manager.filter(**{'%s__exact' % self.name: getattr(instance, self.attname)}):
                os.remove(file_name)

    def get_manipulator_field_objs(self):
        return [oldforms.FileUploadField, oldforms.HiddenField]

    def get_manipulator_field_names(self, name_prefix):
        return [name_prefix + self.name + '_file', name_prefix + self.name]

    def save_file(self, new_data, new_object, original_object, change, rel):
        upload_field_name = self.get_manipulator_field_names('')[0]
        if new_data.get(upload_field_name, False):
            func = getattr(new_object, 'save_%s_file' % self.name)
            if rel:
                func(new_data[upload_field_name][0]["filename"], new_data[upload_field_name][0]["content"])
            else:
                func(new_data[upload_field_name]["filename"], new_data[upload_field_name]["content"])

    def get_directory_name(self):
        return os.path.normpath(datetime.datetime.now().strftime(self.upload_to))

    def get_filename(self, filename):
        from django.utils.text import get_valid_filename
        f = os.path.join(self.get_directory_name(), get_valid_filename(os.path.basename(filename)))
        return os.path.normpath(f)

class FilePathField(Field):
    def __init__(self, verbose_name=None, name=None, path='', match=None, recursive=False, **kwargs):
        self.path, self.match, self.recursive = path, match, recursive
        Field.__init__(self, verbose_name, name, **kwargs)

    def get_manipulator_field_objs(self):
        return [curry(oldforms.FilePathField, path=self.path, match=self.match, recursive=self.recursive)]

class FloatField(Field):
    empty_strings_allowed = False
    def __init__(self, verbose_name=None, name=None, max_digits=None, decimal_places=None, **kwargs):
        self.max_digits, self.decimal_places = max_digits, decimal_places
        Field.__init__(self, verbose_name, name, **kwargs)

    def get_manipulator_field_objs(self):
        return [curry(oldforms.FloatField, max_digits=self.max_digits, decimal_places=self.decimal_places)]

class ImageField(FileField):
    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, **kwargs):
        self.width_field, self.height_field = width_field, height_field
        FileField.__init__(self, verbose_name, name, **kwargs)

    def get_manipulator_field_objs(self):
        return [oldforms.ImageUploadField, oldforms.HiddenField]

    def contribute_to_class(self, cls, name):
        super(ImageField, self).contribute_to_class(cls, name)
        # Add get_BLAH_width and get_BLAH_height methods, but only if the
        # image field doesn't have width and height cache fields.
        if not self.width_field:
            setattr(cls, 'get_%s_width' % self.name, curry(cls._get_FIELD_width, field=self))
        if not self.height_field:
            setattr(cls, 'get_%s_height' % self.name, curry(cls._get_FIELD_height, field=self))

    def save_file(self, new_data, new_object, original_object, change, rel):
        FileField.save_file(self, new_data, new_object, original_object, change, rel)
        # If the image has height and/or width field(s) and they haven't
        # changed, set the width and/or height field(s) back to their original
        # values.
        if change and (self.width_field or self.height_field):
            if self.width_field:
                setattr(new_object, self.width_field, getattr(original_object, self.width_field))
            if self.height_field:
                setattr(new_object, self.height_field, getattr(original_object, self.height_field))
            new_object.save()

class IntegerField(Field):
    empty_strings_allowed = False
    def get_manipulator_field_objs(self):
        return [oldforms.IntegerField]

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.IntegerField(**defaults)

class IPAddressField(Field):
    def __init__(self, *args, **kwargs):
        kwargs['maxlength'] = 15
        Field.__init__(self, *args, **kwargs)

    def get_manipulator_field_objs(self):
        return [oldforms.IPAddressField]

    def validate(self, field_data, all_data):
        validators.isValidIPAddress4(field_data, None)

class NullBooleanField(Field):
    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        Field.__init__(self, *args, **kwargs)

    def get_manipulator_field_objs(self):
        return [oldforms.NullBooleanField]

class PhoneNumberField(IntegerField):
    def get_manipulator_field_objs(self):
        return [oldforms.PhoneNumberField]

    def validate(self, field_data, all_data):
        validators.isValidPhone(field_data, all_data)

class PositiveIntegerField(IntegerField):
    def get_manipulator_field_objs(self):
        return [oldforms.PositiveIntegerField]

class PositiveSmallIntegerField(IntegerField):
    def get_manipulator_field_objs(self):
        return [oldforms.PositiveSmallIntegerField]

class SlugField(Field):
    def __init__(self, *args, **kwargs):
        kwargs['maxlength'] = kwargs.get('maxlength', 50)
        kwargs.setdefault('validator_list', []).append(validators.isSlug)
        # Set db_index=True unless it's been set manually.
        if not kwargs.has_key('db_index'):
            kwargs['db_index'] = True
        Field.__init__(self, *args, **kwargs)

    def get_manipulator_field_objs(self):
        return [oldforms.TextField]

class SmallIntegerField(IntegerField):
    def get_manipulator_field_objs(self):
        return [oldforms.SmallIntegerField]

class TextField(Field):
    def get_manipulator_field_objs(self):
        return [oldforms.LargeTextField]

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'widget': forms.Textarea, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.CharField(**defaults)

class TimeField(Field):
    empty_strings_allowed = False
    def __init__(self, verbose_name=None, name=None, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
        Field.__init__(self, verbose_name, name, **kwargs)

    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type == 'range':
            value = [str(v) for v in value]
        else:
            value = str(value)
        return Field.get_db_prep_lookup(self, lookup_type, value)

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = datetime.datetime.now().time()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(TimeField, self).pre_save(model_instance, add)

    def get_db_prep_save(self, value):
        # Casts dates into string format for entry into database.
        if value is not None:
            # MySQL will throw a warning if microseconds are given, because it
            # doesn't support microseconds.
            if settings.DATABASE_ENGINE == 'mysql':
                value = value.replace(microsecond=0)
                value = str(value)
            elif settings.DATABASE_ENGINE == 'oracle':
                value = value.replace(microsecond=0)
                # cx_Oracle expects a datetime.datetime to persist into TIMESTAMP field.
                value = datetime.datetime(1900, 1, 1, value.hour, value.minute, value.second)
            else:
                value = str(value)
        return Field.get_db_prep_save(self, value)

    def get_manipulator_field_objs(self):
        return [oldforms.TimeField]

    def flatten_data(self,follow, obj = None):
        val = self._get_val_from_obj(obj)
        return {self.attname: (val is not None and val.strftime("%H:%M:%S") or '')}

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.TimeField(**defaults)

class URLField(CharField):
    def __init__(self, verbose_name=None, name=None, verify_exists=True, **kwargs):
        kwargs['maxlength'] = kwargs.get('maxlength', 200)
        if verify_exists:
            kwargs.setdefault('validator_list', []).append(validators.isExistingURL)
        self.verify_exists = verify_exists
        CharField.__init__(self, verbose_name, name, **kwargs)

    def get_manipulator_field_objs(self):
        return [oldforms.URLField]

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'verify_exists': self.verify_exists, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        defaults.update(kwargs)
        return forms.URLField(**defaults)

class USStateField(Field):
    def get_manipulator_field_objs(self):
        return [oldforms.USStateField]

class XMLField(TextField):
    def __init__(self, verbose_name=None, name=None, schema_path=None, **kwargs):
        self.schema_path = schema_path
        Field.__init__(self, verbose_name, name, **kwargs)

    def get_internal_type(self):
        return "TextField"

    def get_manipulator_field_objs(self):
        return [curry(oldforms.XMLLargeTextField, schema_path=self.schema_path)]

class OrderingField(IntegerField):
    empty_strings_allowed=False
    def __init__(self, with_respect_to, **kwargs):
        self.wrt = with_respect_to
        kwargs['null'] = True
        IntegerField.__init__(self, **kwargs )

    def get_internal_type(self):
        return "IntegerField"

    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False, follow=True):
        return [oldforms.HiddenField(name_prefix + self.name)]
